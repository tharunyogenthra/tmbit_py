from client.torrent_file import TorrentFile

import socket
import bencoding
import random
import threading
import time


class DHT_client:
    def __init__(self, listen_port=6881):
        self.listen_port = listen_port
        self.node_id = self.generate_node_id()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", listen_port))
        self.sock.setblocking(False)
        self.peers = set()
        self.bootstrap_nodes = [
            ("router.bittorrent.com", 6881),
            ("dht.transmissionbt.com", 6881),
            ("router.utorrent.com", 6881),
        ]
        self.transaction_id = 0

    def generate_node_id(self):
        return random.randbytes(20)

    def get_transaction_id(self):
        self.transaction_id += 1
        return str(self.transaction_id).encode()

    def send(self, message, addr):
        try:
            encoded_message = bencoding.bencode(message)
            self.sock.sendto(encoded_message, addr)
        except Exception as e:
            pass

    def decode_peers(self, peers_data):
        peers = []
        if len(peers_data) % 6 != 0:
            return peers

        for i in range(0, len(peers_data), 6):
            peer = peers_data[i : i + 6]
            ip = ".".join(str(b) for b in peer[:4])
            port = (peer[4] << 8) + peer[5]
            peers.append((ip, port))
        return peers

    def receive(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                try:
                    response = bencoding.bdecode(data)
                    self.handle_response(response)
                except Exception as e:
                    pass
            except BlockingIOError:
                continue
            except Exception as e:
                pass

    def handle_response(self, response):
        try:
            if b"y" not in response:
                return

            if response[b"y"] == b"r" and b"r" in response:
                r = response[b"r"]
                if b"values" in r:
                    for peers_data in r[b"values"]:
                        new_peers = self.decode_peers(peers_data)
                        for peer in new_peers:
                            if peer[1] > 1024:
                                self.peers.add(peer)
                if b"nodes" in r:
                    nodes = self.decode_nodes(r[b"nodes"])
                    for node in nodes:
                        self.get_peers_from_node(node)
            elif response[b"y"] == b"e":
                pass
        except Exception as e:
            pass

    def decode_nodes(self, nodes_data):
        nodes = []
        if len(nodes_data) % 26 != 0:
            return nodes

        for i in range(0, len(nodes_data), 26):
            node = nodes_data[i : i + 26]
            node_id = node[:20]
            ip = ".".join(str(b) for b in node[20:24])
            port = (node[24] << 8) + node[25]
            nodes.append((node_id, ip, port))
        return nodes

    def get_peers_from_node(self, node):
        _, ip, port = node
        msg = {
            b"t": self.get_transaction_id(),
            b"y": b"q",
            b"q": b"get_peers",
            b"a": {b"id": self.node_id, b"info_hash": self.info_hash},
        }
        self.send(msg, (ip, port))

    def find_nodes(self):
        msg = {
            b"t": self.get_transaction_id(),
            b"y": b"q",
            b"q": b"find_node",
            b"a": {b"id": self.node_id, b"target": self.generate_node_id()},
        }
        for node in self.bootstrap_nodes:
            self.send(msg, node)

    def run(self, info_hash, duration):
        self.info_hash = info_hash
        receive_task = threading.Thread(target=self.receive)
        receive_task.daemon = True
        receive_task.start()
        self.find_nodes()
        time.sleep(duration)

    def get_successful_peers(self):
        return self.peers

    def close(self):
        self.sock.close()


def tracker_request(torrent, duration=5):
    info_hash = bytes.fromhex(torrent.get_info_hash())
    dht_client = DHT_client()
    dht_client.run(info_hash, duration)
    successful_peers = dht_client.get_successful_peers()
    dht_client.close()
    print(successful_peers)
    torrent.set_peers(
        [
            ":".join([str(addr_port_pair) for addr_port_pair in domains])
            for domains in successful_peers
        ]
    )
    return successful_peers
