import os
import socket
import hashlib
from .torrent_file import TorrentFile
from .tracker import tracker_request

def download(torrentFile: TorrentFile, update_signal) -> None:
    try:
        data = peer_handshake(torrentFile, update_signal)
        if data is None:
            update_signal("Download failed during handshake.")
            return
        
        os.makedirs("tmp_torrent", exist_ok=True)
        fp = os.path.join("tmp_torrent", "out.bin")
        
        with open(fp, 'wb') as file:
            file.write(data)
        
        update_signal("Download completed and saved to 'tmp_torrent/out.bin'.")

    except Exception as e:
        update_signal(f"Error during download: {str(e)}")


def peer_handshake_msg(torrentFile: TorrentFile):        
    bittorrent_protocol_string = b"BitTorrent protocol"
    reserved = b'\x00' * 8
    info_hash = bytes.fromhex(torrentFile.get_info_hash())
    peer_id = os.urandom(20)

    handshake_msg = (
        b'\x13' +
        bittorrent_protocol_string + 
        reserved + 
        info_hash + 
        peer_id 
    )

    return handshake_msg
    

def peer_handshake(torrentFile: TorrentFile, update_signal) -> bytes:    
    if torrentFile.get_tracker_info() is None:
        tracker_request(torrentFile)

    update_signal("Attempting handshake with peer")

    try:
        tracker_info = torrentFile.get_tracker_info().get_peers()[0]
        update_signal(f"Peer tracker info: {tracker_info}")
        
        address, port = tracker_info.split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(60)

        update_signal(f"Connecting to peer at {address}:{port}")
        sock.connect((address, int(port)))

        handshake_msg = peer_handshake_msg(torrentFile)
        sock.send(handshake_msg)
        
        response = sock.recv(68)
        update_signal("Received handshake response.")

    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        update_signal(f"Connection error: {e}")
        return None
    
    # Receive the bitfield message
    bitfield_msg = sock.recv(1024)
    update_signal(f"bitfield_msg\nlen={bitfield_msg[0:4]}\nmessage id={bitfield_msg[4:5]}\npayload={bitfield_msg[5:]}")
    update_signal(f"Size rec of pieces is {len(torrentFile.get_info().get_pieces())}")

    if bitfield_msg[4:5] == b'\x05':
        interest_msg = (
            b'\x00\x00\x00\x01' + 
            b'\x02'
        )
        sock.send(interest_msg)
        unchoke_msg = sock.recv(1024)
        update_signal(f"Received unchoke_msg: {unchoke_msg}")
        
        if unchoke_msg[4:5] == b'\x01':
            file_length = sum([file.get_length() for file in torrentFile.get_info().get_files()])
            piece_length = torrentFile.get_info().get_piece_length() 
            data = bytearray()
            piece_index = 0
            default_block_size = 2**14
            pieces_expected = torrentFile.get_info().get_pieces()
            pieces_actual = []
            
            while piece_index < len(pieces_expected):
                piece = b''
                for offset in range(0, piece_length, default_block_size):
                    if piece_index * piece_length + offset >= file_length:
                        break  # No more data to download

                    request_length = min(default_block_size, file_length - (piece_index * piece_length + offset))
                    piece_request_message = (
                        (13).to_bytes(4, byteorder='big') + 
                        b'\x06' + 
                        piece_index.to_bytes(4, byteorder='big') + 
                        offset.to_bytes(4, byteorder='big') +      
                        request_length.to_bytes(4, byteorder='big') 
                    )
                    
                    sock.sendall(piece_request_message)
                    
                    message = receive_message(sock)
                    if message is None:
                        update_signal("Failed to receive piece; retrying with next available peer.")
                        sock.close()
                        return None

                    piece += message[13:]  # Extract the piece data
                    data.extend(message[13:])

                pieces_actual.append(hashlib.sha1(piece).hexdigest())
                piece_index += 1
            
            if len(pieces_actual) != len(pieces_expected):
                update_signal("Download error: Incorrect number of pieces.")
            
            for i in range(len(pieces_actual)):
                if pieces_actual[i] != pieces_expected[i]:
                    update_signal(f"Download failed: Mismatched hash for piece {i}.")
            
            sock.close()
            return data
            
        else:
            update_signal("Did not receive expected unchoke message.")
            sock.close()
    else:
        update_signal("Unexpected message ID in bitfield message.")
        sock.close()


def receive_message(sock):
    try:
        length_msg = sock.recv(4)
        if not length_msg:
            return None
        message_length = int.from_bytes(length_msg, byteorder='big')
        
        message = sock.recv(message_length)
        while len(message) < message_length:
            message += sock.recv(message_length - len(message))
        return length_msg + message
    except socket.timeout:
        print("Timed out waiting for peer response.")
        return None