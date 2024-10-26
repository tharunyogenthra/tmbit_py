import unittest
from client.downloader import download
from client.parse import parse_torrent_file

# Do i gotta test for no internet

class testing(unittest.TestCase):
    def testing_if_peer_handshake_works_for_sample(self):
        ptf = parse_torrent_file("tests/torrents/sample.torrent")
        print(download(ptf))
if __name__ == "__main__":
    unittest.main()