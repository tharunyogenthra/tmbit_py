import subprocess
import requests
from client.torrent_file import TorrentFile, TrackerInfo
from client.parse import parse_tracker_response


import subprocess

import subprocess

def ping_url(url):
    domain = url.split("//")[-1].split("/")[0].split(":")[0]
    try:
        with subprocess.Popen(["ping", domain], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            first_line = process.stdout.readline().strip()  
            # print(first_line)
            if "PING" in first_line:  
                # print(f"Ping to {domain} successful.")
                return True
            else:
                # print(f"Ping to {domain} failed.")
                return False
    except Exception as e:
        # print(f"An error occurred while pinging {domain}: {e}")
        return False



def tracker_request(torrent: TorrentFile):
    info_hash = bytes.fromhex(torrent.get_info_hash())

    if len(torrent.get_info().get_files()) != 1:
        left_download = sum(
            list(map(lambda f: f.get_length(), torrent.get_info().get_files()))
        )
    else:
        left_download = torrent.get_info().get_files()[0].get_length()

    all_urls = [torrent.get_announce()] + torrent.get_announce_list()

    for tracker_url in all_urls:
        if not tracker_url.startswith("http"):
            continue


        if not ping_url(tracker_url):
            # print(f"Skipping tracker {tracker_url}")
            continue

        params = {
            "info_hash": info_hash,
            "peer_id": "-THARUN-easteregglol",
            "port": 6841,
            "uploaded": 0,
            "downloaded": 0,
            "left": left_download,
            "compact": "1",
        }

        try:
            response = requests.get(tracker_url, params=params, timeout=3)

            if response.status_code == 200:
                # print(f"Successfully contacted tracker: {tracker_url}")
                # print(response.content)

                response_dict = parse_tracker_response(response.content)

                torrent.set_tracker_info(
                    TrackerInfo(
                        tracker_url,
                        response_dict.get(b"complete", None),
                        response_dict.get(b"incomplete", None),
                        response_dict.get(b"interval", None),
                        response_dict.get(b"min interval", None),
                        extract_peers(response_dict.get(b"peers", None)),
                    )
                )

                return torrent.get_tracker_info()

            else:
                # print(
                #     f"Tracker request failed {tracker_request}"
                # )
                pass

        except requests.Timeout:
            # Realistically will never happen
            # print(f"Tracker request to {tracker_url} timed out.")
            pass
        except requests.RequestException as e:
            # print(
            #     f"An error occurred while making the tracker request to {tracker_url}: {e}"
            # )
            pass

    # print("No valid HTTP tracker could be contacted.")
    return None


def extract_peers(peers: bytes):
    if peers is None:
        return []

    peers_list = []

    for i in range(0, len(peers), 6):
        ip_bytes = peers[i : i + 4]
        ip_address = ".".join(str(b) for b in ip_bytes)

        port_bytes = peers[i + 4 : i + 6]
        port = int.from_bytes(port_bytes, byteorder="big")

        peers_list.append(f"{ip_address}:{port}")

    return peers_list
