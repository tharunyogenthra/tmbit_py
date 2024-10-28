import unittest
from client.downloader import download
from client.parse import parse_torrent_file
from client.tracker import tracker_request

def main():
    
    ptf = parse_torrent_file("tests/torrents/UnderTale6841.torrent")
    tracker_request(ptf, duration=10)
    download(ptf)
    
    
main()

