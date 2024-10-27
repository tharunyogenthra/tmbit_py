import os
import socket
from client.torrent_file import TorrentFile, TorrentInfo, File
from client.tracker import TrackerInfo, tracker_request
import hashlib

def download(torrentFile: TorrentFile) -> None:
    data = peer_handshake(torrentFile)
    os.makedirs("tmp_torrent", exist_ok=True)
    fp = os.path.join("tmp_torrent", "out.bin")
    
    with open(fp, 'wb') as file:
        file.write(data)


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
    

def peer_handshake(torrentFile: TorrentFile):    
    if torrentFile.get_tracker_info() is None:
        tracker_request(torrentFile)

    print("Attempting handshake with peer")

    try:
        tracker_info = torrentFile.get_tracker_info().get_peers()[0]
        print("Peer tracker info:", tracker_info)
        
        address, port = tracker_info.split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # variable time limit
        sock.settimeout(60)

        print(f"Connecting to peer at {address}:{port}")
        sock.connect((address, int(port)))

        handshake_msg = peer_handshake_msg(torrentFile)
        sock.send(handshake_msg)
        
        response = sock.recv(68)
        print("Received handshake response:", response)
        
    except ConnectionRefusedError:
        print("Connection refused by peer.")
        # have to find another peer and if that doesnt work get a new announce
    except socket.timeout:
        print("Connection attempt timed out.")
    except OSError as e:
        print(f"Socket error: {e}")
    
    # vary this size
    bitfield_msg = sock.recv(1024)
    # check pieces later
    print(f"bitfield_msg\nlen={bitfield_msg[0:4]}\nmessage id={bitfield_msg[4:5]}\npayload={bitfield_msg[5:]}")
    print(f"Size rec of pieces is {len(torrentFile.get_info().get_pieces())}")
    # if msg id is 5
    # for now assume that this tracker has all pieces
    if bitfield_msg[4:5] == b'\x05':
        interest_msg = (
            b'\x00\x00\x00\x01' + 
            b'\x02'
        )
        sock.send(interest_msg)
        unchoke_msg = sock.recv(1024)
        print(f"unchoke_msg msgid = {unchoke_msg}")
        # If msg id is 1 for unchoke we good; payload is normally empty
        if unchoke_msg[4:5] == b'\x01':
            # Time to request for pieces
            # piece size for eg is 32kib but we can only req 16kib each time
            file_length = sum([file.get_length() for file in torrentFile.get_info().get_files()])
            piece_length = torrentFile.get_info().get_piece_length() 
            data = bytearray()
            piece_index = 0
            piece_counter = 0
            default_block_size = 2**14
            pieces_expected = torrentFile.get_info().get_pieces()
            piece = b''
            pieces_actual = []
            
            for _ in range(0, file_length, piece_length):
            
                for offset in range(0, piece_length, default_block_size):
                    if ((file_length - (default_block_size * piece_counter)) < default_block_size):
                        request_length = file_length - (default_block_size * piece_counter)
                    else:
                        request_length = default_block_size
                        
                    piece_counter += 1 
                    piece_request_message = (
                        (13).to_bytes(4, byteorder='big') + 
                        b'\x06' + 
                        piece_index.to_bytes(4, byteorder='big') + 
                        offset.to_bytes(4, byteorder='big') +      
                        request_length.to_bytes(4, byteorder='big') 
                    )
                    
                    # import struct
                    # print("Requesting block, with payload:")
                    # print(piece_request_message)
                    # print(struct.unpack(">IBIII", piece_request_message))
                    
                    sock.sendall(piece_request_message)
                    
                    def receive_message(res):
                        length_msg = res.recv(4)
                        while not length_msg or not int.from_bytes(length_msg, byteorder='big'):
                            length_msg = res.recv(4)
                        message = res.recv(int.from_bytes(length_msg, byteorder='big'))
                        while len(message) < int.from_bytes(length_msg, byteorder='big'):
                            message += res.recv(int.from_bytes(length_msg, byteorder='big') - len(message))
                        return length_msg + message
                    
                    message = receive_message(sock)
                    piece += message[13:]
                    # hash message
                    data.extend(message[13:])

                pieces_actual.append(hashlib.sha1(piece).hexdigest())
                piece = b'' # resetting it every piece
                piece_index += 1
            
            
            # verify download
            if (len(pieces_actual) != len(pieces_expected)):
                print("ERROR download")
            for i in range(0, len(pieces_actual)):
                if (pieces_actual[i] != pieces_expected[i]):
                    print("Download failed")
                
            sock.close()
            return data
            
        else:
            print("The message if for message is not 1")
            sock.close()
    else:
        print("The message id for message is not 5")
        sock.close()