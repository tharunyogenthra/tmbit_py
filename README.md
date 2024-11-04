# tmbit_py

**tmbit_py** is an extremely lightweight, leech-only torrent client built for the **Extended Security Engineering and Cybersecurity (COMP6841)** course at **UNSW**. This client provides the fundamental features necessary for torrenting, with a focus on security and simplicity.

## Features

- **Bencode Parsing**: Parses `.torrent` files using the Bencode format.
- **DHT Tracker Access**: Uses a decentralized tracker network, reducing dependency on centralized trackers.
- **File Writing**: Writes files in the correct format, ensuring data accuracy.
- **User-Friendly GUI**: Simple and sleek graphical interface for easy usage.

## Security Highlights

- **Thread Safety**: Protects against concurrency-related vulnerabilities, ensuring safe, multi-threaded operation.
- **Network Security**: Highlights access points and uses a decentralized tracker, reducing exposure to external networks.
- **Data Integrity**: Ensures files are free from corruption after download.

# How to Run tmbit_py

To run the program, use the following commands in a terminal while inside the `tmbit_py` directory:

MAC: `./dist/tmbit_py_mac` 

WINDOWS: `dist\tmbit_py_windows.exe`  

LINUX: `./dist/tmbit_py_linux`

From here it’s quite intuitive using the GUI and the output will be written to a tmp_torrent directory in which you can 
access all torrents downloaded using our client 

# Usage Demonstration

![Demonstration](docs/tmbit_demo.gif)
