"""Write a Windows shortcut (.lnk) in pure Python.

The usual ways (PowerShell's WScript.Shell, pywin32) are blocked or missing
on PCs with Smart App Control or other application control policies, which
put PowerShell in Constrained Language Mode. This writes the file format
directly (MS-SHLLINK): a LinkInfo block with the target path, plus the
working folder, arguments and icon as strings. Explorer resolves the rest.
"""
from __future__ import annotations

import struct
import uuid
from pathlib import PureWindowsPath

HAS_LINK_INFO = 0x02
HAS_NAME = 0x04
HAS_WORKING_DIR = 0x10
HAS_ARGUMENTS = 0x20
HAS_ICON_LOCATION = 0x40
IS_UNICODE = 0x80
SHELL_LINK_CLSID = uuid.UUID("00021401-0000-0000-C000-000000000046").bytes_le
SW_SHOWNORMAL = 1


def _string(text: str) -> bytes:
    data = text.encode("utf-16-le")
    return struct.pack("<H", len(data) // 2) + data


def _link_info(target: str) -> bytes:
    # VolumeID for a fixed drive with an empty label.
    volume = struct.pack("<IIII", 0x11, 3, 0, 0x10) + b"\x00"
    header_size = 0x24  # includes the Unicode path offsets
    try:
        ansi_path = target.encode("mbcs", "replace") + b"\x00"  # the system code page, on Windows
    except LookupError:
        ansi_path = target.encode("ascii", "replace") + b"\x00"
    suffix = b"\x00"
    unicode_path = target.encode("utf-16-le") + b"\x00\x00"
    unicode_suffix = b"\x00\x00"

    volume_offset = header_size
    path_offset = volume_offset + len(volume)
    suffix_offset = path_offset + len(ansi_path)
    unicode_path_offset = suffix_offset + len(suffix)
    unicode_suffix_offset = unicode_path_offset + len(unicode_path)
    size = unicode_suffix_offset + len(unicode_suffix)
    header = struct.pack("<IIIIIIIII", size, header_size, 0x1, volume_offset, path_offset, 0,
                         suffix_offset, unicode_path_offset, unicode_suffix_offset)
    return header + volume + ansi_path + suffix + unicode_path + unicode_suffix


def shortcut_bytes(target: str, arguments: str = "", working_dir: str = "",
                   icon: str = "", description: str = "") -> bytes:
    target = str(PureWindowsPath(target))
    flags = HAS_LINK_INFO | IS_UNICODE | HAS_NAME | HAS_WORKING_DIR | HAS_ARGUMENTS | HAS_ICON_LOCATION
    header = struct.pack("<I16sII", 0x4C, SHELL_LINK_CLSID, flags, 0x20)  # FILE_ATTRIBUTE_ARCHIVE
    header += b"\x00" * 24  # creation, access, write times: unknown
    header += struct.pack("<IiIHHII", 0, 0, SW_SHOWNORMAL, 0, 0, 0, 0)
    assert len(header) == 0x4C
    strings = b"".join(_string(s) for s in (description, working_dir, arguments, icon or target))
    return header + _link_info(target) + strings + b"\x00\x00\x00\x00"


def write_shortcut(path, target: str, arguments: str = "", working_dir: str = "",
                   icon: str = "", description: str = "") -> None:
    with open(path, "wb") as f:
        f.write(shortcut_bytes(target, arguments, working_dir, icon, description))
