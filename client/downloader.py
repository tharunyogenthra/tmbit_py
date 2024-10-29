import os
import socket
from client.torrent_file import TorrentFile
from client.tracker import tracker_request
import hashlib
import time

def download(torrentFile: TorrentFile, progress_callback=None):
    if progress_callback:
        progress_callback("Initializing download...")
    
    # Initialize by making tracker request first
    if progress_callback:
        progress_callback("Contacting tracker for peers...")
    
    try:
        tracker_response = tracker_request(torrentFile, 10)
        if not tracker_response:
            if progress_callback:
                progress_callback("Error: Failed to connect to tracker")
            return None
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error contacting tracker: {e}")
        return None
    
    # Initialize pieces dictionary
    pieces_dict = {i: b'' for i in range(len(torrentFile.get_info().get_pieces()))}
    
    # Get peers from torrent file (should be populated after tracker request)
    peers = torrentFile.get_peers()
    if not peers:
        if progress_callback:
            progress_callback("Error: No peers available")
        return None
        
    peers_piece_dict = connect_to_peers(torrentFile, pieces_dict, progress_callback)
    if not peers_piece_dict:
        if progress_callback:
            progress_callback("Error: Failed to download from peers")
        return None
    
    if progress_callback:
        progress_callback("Creating output directory...")
        
    try:
        os.makedirs("tmp_torrent", exist_ok=True)
        fp = os.path.join("tmp_torrent", "out.bin")
        
        if progress_callback:
            progress_callback("Writing downloaded pieces to file...")
            
        with open(fp, 'wb') as file:
            for pieces in peers_piece_dict.items():
                file.write(pieces[1])
        
        if progress_callback:
            progress_callback("Download complete")
            
        return peers_piece_dict
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error writing file: {e}")
        return None

def receive_message(sock: socket.socket):
    try:
        length_msg = sock.recv(4)
        if not length_msg or not int.from_bytes(length_msg, byteorder='big'):
            return None
        
        message_length = int.from_bytes(length_msg, byteorder='big')
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
    return b'\x00\x00\x00\x01\x02'

def connect_to_peers(torrentFile: TorrentFile, pieces_dict, progress_callback=None):
    # Get peers and handle empty case
    peers = torrentFile.get_peers()
    if not peers:
        if progress_callback:
            progress_callback("No peers available, requesting from tracker...")
        try:
            tracker_request(torrentFile, 10)
            peers = torrentFile.get_peers()
            if not peers:
                if progress_callback:
                    progress_callback("Still no peers available after tracker request")
                return None
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error requesting peers from tracker: {e}")
            return None
    
    peers = [domain.split(":") for domain in peers]
    
    if progress_callback:
        progress_callback(f"Found {len(peers)} peers")
    
    for address, port in [(ele[0], int(ele[1])) for ele in peers]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

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
                continue
            
            if progress_callback:
                progress_callback(f"Successfully connected to {address}:{port}")
                
            if response != b'':
                sock.settimeout(30)
                bitfield_msg = sock.recv(512)
                binary_piece = bin(int.from_bytes(bitfield_msg[5:], 'big'))[2:2+len(torrentFile.get_info().get_pieces())]
                
                if progress_callback:
                    progress_callback(f"Received piece availability from peer")
                
                sock.send(interested_msg())
                unchoke_msg = sock.recv(10)
                
                if unchoke_msg[4:5] != b'\x01':
                    if progress_callback:
                        progress_callback("Peer did not unchoke us, trying next peer")
                    sock.close()
                    continue
                
                if progress_callback:
                    progress_callback(f"Peer {address}:{port} unchoked; beginning downloads")
                
                for piece_index, ele in pieces_dict.items():
                    if (binary_piece[piece_index] == "1" and ele == b''):
                        try:
                            total_length = sum(file.get_length() for file in torrentFile.get_info().get_files())
                        except AttributeError:
                            # Handle single-file torrents
                            total_length = torrentFile.get_info().get_length()
                            
                        piece_length = torrentFile.get_info().get_piece_length()
                        pieces_expected = torrentFile.get_info().get_pieces()
                        default_block_size = 2**14
                        
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
                                (13).to_bytes(4, byteorder='big') +
                                b'\x06' +
                                piece_index.to_bytes(4, byteorder='big') +
                                offset.to_bytes(4, byteorder='big') +
                                request_length.to_bytes(4, byteorder='big')
                            )

                            sock.sendall(request_msg)

                            message = receive_message(sock)
                            if not message or message[4:5] != b'\x07':
                                if progress_callback:
                                    progress_callback(f"Error downloading piece {piece_index + 1}, trying next peer")
                                sock.close()
                                continue
                            
                            piece.extend(message[13:])
                            
                        piece = bytes(piece)
                        pieces_dict[piece_index] = piece
                        
                    if not any(len(val) == 0 for val in pieces_dict.values()):
                        pieces_meta = torrentFile.get_info().get_pieces()
                        if (len(pieces_meta) != len(pieces_dict)):
                            if progress_callback:
                                progress_callback("Download verification failed - piece count mismatch")
                            break
                            
                        for i in range(0, len(pieces_dict)):
                            if (pieces_meta[i] != hashlib.sha1(pieces_dict[i]).hexdigest()):
                                if progress_callback:
                                    progress_callback(f"Download verification failed - hash mismatch at piece {i}")
                                break

                if progress_callback:
                    progress_callback("All pieces downloaded from peer")
                bitfield_msg, binary_piece = None, None
                break
                
        except socket.timeout:
            if progress_callback:
                progress_callback(f"Connection timed out for peer at {address}:{port}")
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error with peer at {address}:{port}: {e}")
        finally:
            sock.close()

    if (any(value == b'' for value in pieces_dict.values())):
        if progress_callback:
            progress_callback("Some pieces missing, requesting new peers from tracker")
        try:
            tracker_request(torrentFile, 10)
            return connect_to_peers(torrentFile, pieces_dict, progress_callback)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error requesting new peers: {e}")
            return None
    
    return pieces_dict