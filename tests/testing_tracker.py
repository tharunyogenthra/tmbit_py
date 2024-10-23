import unittest
from client.tracker import tracker_request
from client.parse import parse_torrent_file

class testing(unittest.TestCase):
    def testing_if_tracker_get_req_works_sample(self):
        ptf = parse_torrent_file("tests/torrents/sample.torrent")
        res = tracker_request(ptf)
        self.assertEqual(type(res.get_complete()), int)
        self.assertEqual(type(res.get_announce()), str)
        self.assertEqual(type(res.get_incomplete()), int)
        self.assertEqual(type(res.get_interval()), int)
        self.assertEqual(type(res.get_min_interval()), int)
        self.assertEqual(type(res.get_peers()), list)
        self.assertGreater(len(res.get_peers()), 0)
        # Cant really test this as trackers are subject to change
        
    def testing_if_tracker_get_req_works_gta5(self):
        ptf = parse_torrent_file("tests/torrents/gta5.torrent")
        res = tracker_request(ptf)
        self.assertEqual(type(res.get_complete()), int)
        self.assertEqual(type(res.get_announce()), str)
        self.assertEqual(type(res.get_incomplete()), int)
        self.assertEqual(type(res.get_interval()), int)
        self.assertEqual(type(res.get_min_interval()), int)
        self.assertEqual(type(res.get_peers()), list)
        self.assertGreater(len(res.get_peers()), 0)
        # Cant really test this as trackers are subject to change
    
    
if __name__ == "__main__":
    unittest.main()

# \xa5\xe8)I\xc9d\xa5\xe8&\xa4\xc9L\xa5\xe8#r\xc8\xed
'''
a5 e8 29 49 c9 64
a5 e8 26 a4 c9 4c
a5 e8 23 72 c8 ed


int.from_bytes(byte_array, byteorder='big', signed=False)

165.232.35.114:51533
165.232.38.164:51596
165.232.41.73:51451
'''