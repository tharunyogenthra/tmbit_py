from typing import List, Optional


class TrackerInfo:
    def __init__(
        self,
        announce: str,
        complete: int,
        incomplete: int,
        interval: int,
        min_interval: int,
        peers: List[str],
    ) -> None:
        self._announce: str = announce
        self._complete: int = complete
        self._incomplete: int = incomplete
        self._interval: int = interval
        self._min_interval: int = min_interval
        self._peers: List[str] = peers

    def get_announce(self) -> str:
        return self._announce if self._announce else None

    def get_complete(self) -> int:
        return self._complete if self._complete is not None else None

    def get_incomplete(self) -> int:
        return self._incomplete if self._incomplete is not None else None

    def get_interval(self) -> int:
        return self._interval if self._interval is not None else None

    def get_min_interval(self) -> int:
        return self._min_interval if self._min_interval is not None else None

    def get_peers(self) -> List[str]:
        return self._peers if self._peers else None


    def __str__(self) -> str:
        return (
            f"TrackerInfo(announce={self._announce}, complete={self._complete}, "
            f"incomplete={self._incomplete}, interval={self._interval}, "
            f"min_interval={self._min_interval}, peers={self._peers}"
        )


class File:
    def __init__(self, length: int, path: List[str]) -> None:
        self._length: int = length
        self._path: List[str] = path

    def get_length(self) -> int:
        return self._length

    def get_path(self) -> List[str]:
        return self._path

    def __str__(self) -> str:
        return f"File(length={self._length}, path={self._path})"


class TorrentInfo:
    def __init__(
        self,
        name: str,
        piece_length: int,
        pieces: Optional[List[str]] = None,
        files: Optional[List[File]] = None,
    ) -> None:
        self._name: str = name
        self._piece_length: int = piece_length
        self._pieces: List[str] = pieces if pieces is not None else []
        self._files: List[File] = files if files is not None else []

    def get_name(self) -> str:
        return self._name

    def get_piece_length(self) -> int:
        return self._piece_length

    def get_pieces(self) -> List[str]:
        return self._pieces

    def get_files(self) -> List[File]:
        return self._files

    def set_name(self, name: str) -> None:
        self._name = name

    def set_piece_length(self, piece_length: int) -> None:
        self._piece_length = piece_length

    def add_piece(self, piece: str) -> None:
        self._pieces.append(piece)

    def add_file(self, torrent_file: File) -> None:
        self._files.append(torrent_file)

    def __str__(self) -> str:
        return (
            f"TorrentInfo(name={self._name}, piece_length={self._piece_length}, "
            f"pieces={self._pieces}, files={', '.join(str(file) for file in self._files)})"
        )


class TorrentFile:
    def __init__(self) -> None:
        self._announce: Optional[str] = None
        self._announce_list: List[str] = []
        self._comment: Optional[str] = None
        self._created_by: Optional[str] = None
        self._creation_date: Optional[int] = None
        self._encoding: Optional[str] = None
        self._url_list: List[str] = []
        self._info: Optional[TorrentInfo] = None
        self._tracker_info: Optional[TrackerInfo] = None
        self._info_hash: Optional[str] = None

    def get_announce(self) -> Optional[str]:
        return self._announce

    def get_announce_list(self) -> List[str]:
        return self._announce_list

    def get_comment(self) -> Optional[str]:
        return self._comment

    def get_created_by(self) -> Optional[str]:
        return self._created_by

    def get_creation_date(self) -> Optional[int]:
        return self._creation_date

    def get_encoding(self) -> Optional[str]:
        return self._encoding

    def get_url_list(self) -> List[str]:
        return self._url_list

    def get_info(self) -> Optional[TorrentInfo]:
        return self._info

    def get_tracker_info(self) -> Optional[TrackerInfo]:
        return self._tracker_info

    def get_info_hash(self) -> Optional[str]:
        return self._info_hash

    def set_announce(self, announce: str) -> None:
        self._announce = announce

    def set_announce_list(self, announce_list: List[str]) -> None:
        self._announce_list = announce_list

    def set_comment(self, comment: str) -> None:
        self._comment = comment

    def set_created_by(self, created_by: str) -> None:
        self._created_by = created_by

    def set_creation_date(self, creation_date: int) -> None:
        self._creation_date = creation_date
        
    def set_encoding(self, encoding: str) -> None:
        self._encoding = encoding

    def set_url_list(self, url_list: List[str]) -> None:
        self._url_list = url_list

    def set_info(self, info: TorrentInfo) -> None:
        self._info = info

    def set_tracker_info(self, tracker_info: TrackerInfo) -> None:
        self._tracker_info = tracker_info

    def set_info_hash(self, info_hash: str) -> None:
        self._info_hash = info_hash

    def __str__(self) -> str:
        return (
            f"TorrentFile(announce={self._announce}, announce_list={self._announce_list}, "
            f"comment={self._comment}, created_by={self._created_by}, "
            f"creation_date={self._creation_date}, encoding={self._encoding}, "
            f"url_list={self._url_list}, info={self._info}, "
            f"tracker_info={self._tracker_info}, info_hash={self._info_hash})"
        )
