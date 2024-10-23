import os
import bencoding
from client.torrent_file import TorrentFile, TorrentInfo, File
import hashlib
from typing import List

def parse_tracker_response(response: bytes) -> List[int]:
    return bencoding.bdecode(response)

def parse_torrent_file(path: str) -> TorrentFile:
    if not os.path.exists(path):
        raise FileNotFoundError(f"The file at {path} does not exist.")

    with open(path, "rb") as unparsed_torrent:
        try:
            torrent_file = TorrentFile()
            torrent_dict = bencoding.bdecode(unparsed_torrent.read())
            torrent_file.set_announce(torrent_dict[b"announce"].decode())

            torrent_file.set_announce_list(
                [
                    url.decode()
                    for sublist in torrent_dict.get(b"announce-list", [])
                    for url in sublist
                ]
            )

            # Using .get() to make fields optional
            torrent_file.set_comment(torrent_dict.get(b"comment", b"").decode())
            torrent_file.set_created_by(torrent_dict.get(b"created by", b"").decode())
            torrent_file.set_creation_date(torrent_dict.get(b"creation date", None))
            torrent_file.set_encoding(torrent_dict.get(b'encoding', b"").decode())
            torrent_file.set_url_list(
                [url.decode() for url in torrent_dict.get(b"url-list", [])]
            )
            torrent_file.set_info_hash(
                hashlib.sha1(bencoding.bencode(torrent_dict[b"info"])).hexdigest()
            )

            torrent_info = TorrentInfo(
                torrent_dict[b"info"][b"name"].decode(), 
                torrent_dict[b"info"][b"piece length"]
            )

            for file in torrent_dict[b"info"].get(b"files", []):
                torrent_info.add_file(File(file[b"length"], file[b"path"][0].decode()))
                
            if (len(torrent_info.get_files()) == 0):
                torrent_info.add_file(File(torrent_dict[b"info"][b'length'], torrent_dict[b"info"][b'name']))

            pieces = torrent_dict[b"info"][b"pieces"]
            for i in range(0, len(pieces), 20):
                # zfill is a really cool function that adds zeros to the left.
                # this makes 0x6 -> 0x06 which makes the pieces hashes align
                torrent_info.add_piece(
                    "".join(
                        list(
                            map(
                                lambda x: hex(x)[2:].zfill(2),
                                pieces[i : i + 20],
                            )
                        )
                    )
                )

            torrent_file.set_info(torrent_info)

            return torrent_file
        except Exception as e:
            raise RuntimeError(
                f"Failed to parse (maybe txt; has to be valid bencode): {e}"
            )
