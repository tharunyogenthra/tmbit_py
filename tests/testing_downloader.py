import unittest
from client.downloader import download
from client.parse import parse_torrent_file
import os
import hashlib

class Testing(unittest.TestCase):        
    def get_file_hash(self, file_path):
            sha1 = hashlib.sha1()
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha1.update(chunk)
            return sha1.hexdigest()
        
    def test_peer_handshake_works_for_sample(self):
        ptf = parse_torrent_file("tests/torrents/sample.torrent")
        download(ptf)
        
        expected_file_out = "tests/torrents/sample.txt"
        created_file_out = os.path.join("tmp_torrent", "out.bin")

        self.assertEqual(self.get_file_hash(expected_file_out), self.get_file_hash(created_file_out))
    
    def tearDown(self):
        output_file = os.path.join("tmp_torrent", "out.bin")
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == "__main__":
    unittest.main()