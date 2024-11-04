import unittest
from client.downloader import download
from client.parse import parse_torrent_file
from client.tracker import tracker_request

def main():
    
    ptf = parse_torrent_file("tests/torrents/bitcoin.torrent")
    tracker_request(ptf)
    download(ptf)
    
    
main()

