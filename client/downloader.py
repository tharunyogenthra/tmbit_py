import os
import socket
from client.torrent_file import TorrentFile
from client.tracker import tracker_request
import hashlib
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque

def download(torrentFile: TorrentFile, progress_callback=None):
    if progress_callback:
        progress_callback("Initializing download...")
    
    # Initialize by making tracker request first
    if progress_callback:
        progress_callback("Contacting tracker for peers...")
    
    try:
        tracker_response = tracker_request(torrentFile)
        if not tracker_response:
            if progress_callback:
                progress_callback("Error: Failed to connect to tracker")
            return None
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error contacting tracker: {e}")
        return None

    msg = connect_to_peers(torrentFile, progress_callback)
    if not msg:
        if progress_callback:
            progress_callback("Error: Failed to download from peers")
        return None

    if progress_callback:
        progress_callback("Creating output directory...")
        
    folder = "tmp_torrent"
    try:
        os.makedirs(folder, exist_ok=True)
        
        if progress_callback:
            progress_callback("Writing downloaded pieces to file...")
            
        output_filename = os.path.join(folder, torrentFile.get_info().get_files()[0].get_path().decode('utf-8'))
        with open(output_filename, "wb") as file:
            file.write(msg)
            
        if progress_callback:
            progress_callback("Download complete")
            
        return msg
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error writing file: {e}")
        return None

def receive_message(sock: socket.socket):
    try:
        length_msg = sock.recv(4)
        if not length_msg or not int.from_bytes(length_msg, byteorder="big"):
            return None

        message_length = int.from_bytes(length_msg, byteorder="big")
        message = sock.recv(message_length)

        while len(message) < message_length:
            chunk = sock.recv(message_length - len(message))
            if not chunk:
                break
            message += chunk

        return length_msg + message
    except socket.error as e:
        return None

def peer_handshake_msg(torrentFile: TorrentFile):
    bittorrent_protocol_string = b"BitTorrent protocol"
    reserved = b"\x00" * 8
    info_hash = bytes.fromhex(torrentFile.get_info_hash())
    peer_id = os.urandom(20)
    return b"\x13" + bittorrent_protocol_string + reserved + info_hash + peer_id

def interested_msg():
    return b"\x00\x00\x00\x01\x02"

def connect_to_single_peer(torrentFile: TorrentFile, address: str, port: int, socks, progress_callback=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)

    try:
        if progress_callback:
            progress_callback(f"Connecting to peer at {address}:{port}")
            
        sock.connect((address, port))

        handshake_msg = peer_handshake_msg(torrentFile)
        sock.send(handshake_msg)

        response = sock.recv(68)
        if not response:
            if progress_callback:
                progress_callback(f"No response from {address}:{port}, trying next peer")
            sock.close()
            return

        if response != b"":
            sock.settimeout(10)
            bitfield_msg = sock.recv(512)
            binary_piece = bin(int.from_bytes(bitfield_msg[5:], "big"))[
                2 : 2 + len(torrentFile.get_info().get_pieces())
            ]

            if progress_callback:
                progress_callback(f"Received piece availability from peer")

            sock.send(interested_msg())
            unchoke_msg = sock.recv(10)

            if unchoke_msg[4:5] != b"\x01":
                if progress_callback:
                    progress_callback("Peer did not unchoke us, trying next peer")
                sock.close()
            else:
                if progress_callback:
                    progress_callback(f"Peer {address}:{port} unchoked; beginning downloads")
                socks.append((binary_piece, sock))
        else:
            sock.close()

    except socket.timeout:
        if progress_callback:
            progress_callback(f"Connection timed out for peer at {address}:{port}")
        sock.close()
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error with peer at {address}:{port}: {e}")
        sock.close()

def connect_to_peers(torrentFile: TorrentFile, progress_callback=None):
    peers = [domain.split(":") for domain in torrentFile.get_peers()]
    if not peers:
        if progress_callback:
            progress_callback("No peers available")
        return None

    if progress_callback:
        progress_callback(f"Found {len(peers)} peers")

    socks = []
    with ThreadPoolExecutor(max_workers=len(peers)) as executor:
        futures = {
            executor.submit(
                connect_to_single_peer, torrentFile, address, int(port), socks, progress_callback
            ): (address, port)
            for address, port in peers
        }

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error occurred for peer: {e}")

    return download_from_socks(torrentFile, socks, progress_callback)

def download_a_single_piece(torrentFile: TorrentFile, sock, piece_index, progress_callback=None):
    sock.settimeout(10)
    try:
        total_length = sum(file.get_length() for file in torrentFile.get_info().get_files())
    except AttributeError:
        total_length = torrentFile.get_info().get_length()
        
    piece_length = torrentFile.get_info().get_piece_length()
    pieces_expected = torrentFile.get_info().get_pieces()
    default_block_size = 2 ** 14

    piece = bytearray()
    current_piece_length = (
        total_length - (piece_index * piece_length)
        if piece_index == len(pieces_expected) - 1
        else piece_length
    )

    if progress_callback:
        progress_callback(f"Downloading piece {piece_index + 1}/{len(pieces_expected)}")

    for offset in range(0, current_piece_length, default_block_size):
        remaining = current_piece_length - offset
        request_length = min(default_block_size, remaining)

        request_msg = (
            (13).to_bytes(4, byteorder="big")
            + b"\x06"
            + piece_index.to_bytes(4, byteorder="big")
            + offset.to_bytes(4, byteorder="big")
            + request_length.to_bytes(4, byteorder="big")
        )

        try:
            sock.sendall(request_msg)
        except (BrokenPipeError, socket.timeout):
            return None

        message = receive_message(sock)
        if not message or message[4:5] != b"\x07":
            return None

        piece.extend(message[13:])

    return bytes(piece)

def download_from_socks(torrentFile: TorrentFile, socks, progress_callback=None):
    pieces_dict = {i: b'' for i in range(len(torrentFile.get_info().get_pieces()))}
    socks_map = {sock[1]: 0 for sock in socks}
    print(socks_map)
    pieces_queue = deque(range(len(torrentFile.get_info().get_pieces())))
    
    while pieces_queue:
        # lil filtering system i got to kick out bum peers
        socks_map = {sock: value for sock, value in socks_map.items() if value <= 3}
        if not socks_map:
            if progress_callback:
                progress_callback("Error: Failed to download from peers.")
            return None
            
        for sock, _ in socks_map.items():
            if pieces_queue:
                index = pieces_queue.popleft()
            else:
                break
                
            res = download_a_single_piece(torrentFile, sock, index, progress_callback)
            if res is None:
                pieces_queue.append(index)
                socks_map[sock] += 1
            else:
                pieces_dict[index] = res

    # Verify pieces
    pieces_meta = torrentFile.get_info().get_pieces()
    if len(pieces_meta) != len(pieces_dict):
        if progress_callback:
            progress_callback("Download verification failed - piece count mismatch")
        return None
        
    for i in range(len(pieces_dict)):
        if pieces_meta[i] != hashlib.sha1(pieces_dict[i]).hexdigest():
            if progress_callback:
                progress_callback(f"Download verification failed - hash mismatch at piece {i}")
            return None
            
    if progress_callback:
        progress_callback("All pieces downloaded from peers")
        
    return b"".join(pieces_dict.values())