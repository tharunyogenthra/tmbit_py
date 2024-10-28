import os
import socket
from client.torrent_file import TorrentFile
from client.tracker import tracker_request
import hashlib
import time

def download(torrentFile: TorrentFile):
    peers_piece_dict = connect_to_peers(torrentFile, {i: b'' for i in range(len(torrentFile.get_info().get_pieces()))})
    
    os.makedirs("tmp_torrent", exist_ok=True)
    
    fp = os.path.join("tmp_torrent", "out.bin")
    
    with open(fp, 'wb') as file:
        for pieces in peers_piece_dict.items():
            file.write(pieces[1])
    
    return peers_piece_dict

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
        print(f"Socket error while receiving message: {e}")
        return None


            
def peer_handshake_msg(torrentFile: TorrentFile):
    bittorrent_protocol_string = b"BitTorrent protocol"
    reserved = b"\x00" * 8
    info_hash = bytes.fromhex(torrentFile.get_info_hash())
    peer_id = os.urandom(20)
    return b"\x13" + bittorrent_protocol_string + reserved + info_hash + peer_id

def interested_msg():
    return b'\x00\x00\x00\x01\x02'

def connect_to_peers(torrentFile: TorrentFile, pieces_dict):
    peers = [domain.split(":") for domain in torrentFile.get_peers()]
    
    for address, port in [(ele[0], int(ele[1])) for ele in peers]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        try:
            print(f"Attempting to connect to peer at {address}:{port}")
            sock.connect((address, port))

            handshake_msg = peer_handshake_msg(torrentFile)
            sock.send(handshake_msg)

            response = sock.recv(68)
            if not response:
                print(f"No response from {address}:{port}, closing socket.")
                sock.close()
                continue
            
            print(f"Received handshake response from {address}:{port}:", response)
            if response != b'':
                sock.settimeout(30)
                # this will need to be adjusted for massive files might have to do a realloc
                bitfield_msg = sock.recv(512)
                binary_piece = bin(int.from_bytes(bitfield_msg[5:], 'big'))[2:2+len(torrentFile.get_info().get_pieces())]
                
                print(f"All pieces avaiable are {binary_piece}")
                # might have to call it repeatedly
                sock.send(interested_msg())
                unchoke_msg = sock.recv(10)
                print(f"unchoke is {unchoke_msg}")
                if unchoke_msg[4:5] != b'\x01':
                    print("Peer did not unchoke us, trying next peer")
                    sock.close()
                    # fuck this peer we are moving on
                    continue
                
                print(f"{address}:{port} unchoked; beginning piece downloads")
                
                for piece_index, ele in pieces_dict.items():
                    if (binary_piece[piece_index] == "1" and ele == b''):
                        # pieces_dict[piece_index] = download_piece()
                        # if it downloads then very good
                        # if it doesnt download for any cancer error just move along

                        total_length = sum(file.get_length() for file in torrentFile.get_info().get_files())
                        piece_length = torrentFile.get_info().get_piece_length()
                        pieces_expected = torrentFile.get_info().get_pieces()
                        default_block_size = 2**14
                        
                        piece = bytearray()
                        current_piece_length = (
                            total_length - (piece_index * piece_length)
                            if piece_index == len(pieces_expected) - 1
                            else piece_length
                        )
                        
                        print(f"Downloading piece {piece_index + 1}/{len(pieces_expected)}")
                        
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
                                # if it breaks halfway through dict should be intact and we just go next peers
                                # print(f"message is {message}")
                                print(f"Unexpected or empty message, skipping peer")
                                sock.close()
                                continue
                            
                            piece.extend(message[13:])
                            
                        piece = bytes(piece)
                        pieces_dict[piece_index] = piece
                        
                    if not any(len(val) == 0 for val in pieces_dict.values()):
                        pieces_meta = torrentFile.get_info().get_pieces()
                        if (len(pieces_meta) != len(pieces_dict)):
                            print("Download got messed up")
                            break
                            
                        for i in range(0, len(pieces_dict)):
                            if (pieces_meta[i] != hashlib.sha1(pieces_dict[i]).hexdigest()):
                                print(f"Hashes are wrong at {i}")
                                break

                print("File finished")
                bitfield_msg, binary_piece = None, None
                break
                
        except socket.timeout:
            print(f"Connection timed out for peer at {address}:{port}.")
        except Exception as e:
            print(f"Unexpected error with peer at {address}:{port}: {e}")
        finally:
            sock.close()

    if (any(value == b'' for value in pieces_dict.values())):
        tracker_request(torrentFile, 10)
        connect_to_peers(torrentFile, pieces_dict)
        print("Aww shit here we go again")
    return pieces_dict
