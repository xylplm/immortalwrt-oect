#!/usr/bin/env python3
"""Inspect an OpenWrt disk image without mounting it.

This is intentionally read-only.  With only the Python standard library it can
parse the partition table, identify common filesystem signatures, and scan
text-like data in the image for OpenWrt first-boot/default-network clues.  If
the optional ``dissect.btrfs`` package is installed, it can also extract target
files from a btrfs rootfs without mounting the image.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import struct
import sys
from dataclasses import dataclass
from typing import Iterable


SECTOR_SIZE = 512
GPT_HEADER_SIGNATURE = b"EFI PART"
BTRFS_MAGIC = b"_BHRfS_M"


@dataclass(frozen=True)
class Partition:
    index: int
    name: str
    first_lba: int
    last_lba: int
    type_guid_hex: str

    @property
    def offset(self) -> int:
        return self.first_lba * SECTOR_SIZE

    @property
    def size(self) -> int:
        return (self.last_lba - self.first_lba + 1) * SECTOR_SIZE


class OffsetReader(io.RawIOBase):
    """Expose a bounded region of a file as a seekable read-only stream."""

    def __init__(self, path: str, offset: int, size: int):
        self._fh = open(path, "rb")
        self._offset = offset
        self._size = size
        self._pos = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence == os.SEEK_SET:
            new_pos = offset
        elif whence == os.SEEK_CUR:
            new_pos = self._pos + offset
        elif whence == os.SEEK_END:
            new_pos = self._size + offset
        else:
            raise ValueError(f"invalid whence: {whence}")

        if new_pos < 0:
            raise ValueError("negative seek position")
        self._pos = new_pos
        return self._pos

    def read(self, size: int = -1) -> bytes:
        if self._pos >= self._size:
            return b""
        if size is None or size < 0:
            size = self._size - self._pos
        else:
            size = min(size, self._size - self._pos)
        self._fh.seek(self._offset + self._pos)
        data = self._fh.read(size)
        self._pos += len(data)
        return data

    def close(self) -> None:
        try:
            self._fh.close()
        finally:
            super().close()


def human_size(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}" if unit != "B" else f"{size} B"
        value /= 1024
    return f"{size} B"


def read_at(path: str, offset: int, size: int) -> bytes:
    with open(path, "rb") as f:
        f.seek(offset)
        return f.read(size)


def parse_gpt(path: str) -> list[Partition]:
    mbr = read_at(path, 0, SECTOR_SIZE)
    if len(mbr) != SECTOR_SIZE or mbr[510:512] != b"\x55\xaa":
        raise ValueError("image does not have an MBR signature")

    gpt_header = read_at(path, SECTOR_SIZE, SECTOR_SIZE)
    if gpt_header[:8] != GPT_HEADER_SIGNATURE:
        raise ValueError("image does not have a GPT header at LBA 1")

    entries_lba = struct.unpack_from("<Q", gpt_header, 72)[0]
    entries_count = struct.unpack_from("<I", gpt_header, 80)[0]
    entry_size = struct.unpack_from("<I", gpt_header, 84)[0]
    entries = read_at(path, entries_lba * SECTOR_SIZE, entries_count * entry_size)

    partitions: list[Partition] = []
    for i in range(entries_count):
        entry = entries[i * entry_size : (i + 1) * entry_size]
        if not entry or entry[:16] == b"\x00" * 16:
            continue

        first_lba = struct.unpack_from("<Q", entry, 32)[0]
        last_lba = struct.unpack_from("<Q", entry, 40)[0]
        name = entry[56 : 56 + 72].decode("utf-16le", errors="ignore").rstrip("\x00")
        partitions.append(
            Partition(
                index=i + 1,
                name=name or f"partition-{i + 1}",
                first_lba=first_lba,
                last_lba=last_lba,
                type_guid_hex=entry[:16].hex(),
            )
        )
    return partitions


def identify_filesystem(path: str, partition: Partition) -> tuple[str, dict[str, str]]:
    ext_super = read_at(path, partition.offset + 1024, 2048)
    if len(ext_super) >= 58 and ext_super[56:58] == b"\x53\xef":
        log_block_size = struct.unpack_from("<I", ext_super, 24)[0]
        block_size = 1024 << log_block_size
        blocks = struct.unpack_from("<I", ext_super, 4)[0]
        label = ext_super[120:136].split(b"\0", 1)[0].decode("ascii", errors="replace")
        return "ext", {
            "block_size": str(block_size),
            "blocks": str(blocks),
            "volume": label,
            "declared_size": human_size(blocks * block_size),
        }

    btrfs_super = read_at(path, partition.offset + 0x10000, 4096)
    if len(btrfs_super) >= 0x12B + 256 and btrfs_super[0x40:0x48] == BTRFS_MAGIC:
        total = struct.unpack_from("<Q", btrfs_super, 0x70)[0]
        bytes_used = struct.unpack_from("<Q", btrfs_super, 0x78)[0]
        root = struct.unpack_from("<Q", btrfs_super, 0x50)[0]
        chunk_root = struct.unpack_from("<Q", btrfs_super, 0x58)[0]
        sectorsize = struct.unpack_from("<I", btrfs_super, 0x90)[0]
        nodesize = struct.unpack_from("<I", btrfs_super, 0x94)[0]
        label = btrfs_super[0x12B : 0x12B + 256].split(b"\0", 1)[0].decode("ascii", errors="replace")
        return "btrfs", {
            "label": label,
            "total": human_size(total),
            "bytes_used": human_size(bytes_used),
            "root_logical": str(root),
            "chunk_root_logical": str(chunk_root),
            "sectorsize": str(sectorsize),
            "nodesize": str(nodesize),
        }

    head = read_at(path, partition.offset, 4096)
    if head[:4] == b"hsqs":
        return "squashfs", {}
    if len(head) >= 1028 and head[1024:1028] == b"\x10\x20\xf5\xf2":
        return "f2fs", {}
    return "unknown", {}


def scan_needles(path: str, needles: Iterable[bytes], chunk_size: int = 1024 * 1024) -> dict[bytes, list[int]]:
    hits = {needle: [] for needle in needles}
    max_needle = max((len(needle) for needle in needles), default=1)
    overlap_size = max(4096, max_needle - 1)
    overlap = b""
    offset = 0

    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            buf = overlap + chunk
            base = offset - len(overlap)
            for needle in needles:
                start = 0
                while True:
                    pos = buf.find(needle, start)
                    if pos < 0:
                        break
                    absolute = base + pos
                    if absolute >= 0 and len(hits[needle]) < 30:
                        hits[needle].append(absolute)
                    start = pos + 1
            overlap = buf[-overlap_size:]
            offset += len(chunk)
    return hits


def printable_context(path: str, offset: int, radius: int = 384) -> list[tuple[int, str]]:
    start = max(0, offset - radius)
    data = read_at(path, start, radius * 2)
    contexts: list[tuple[int, str]] = []
    for match in re.finditer(rb"[\x09\x0a\x0d\x20-\x7e]{4,}", data):
        text = match.group(0).decode("utf-8", errors="replace")
        contexts.append((start + match.start(), text))
    return contexts


def print_partition_report(path: str, partitions: list[Partition]) -> None:
    print("Partitions")
    for p in partitions:
        fs_name, details = identify_filesystem(path, p)
        print(
            f"  {p.index}: {p.name} offset={p.offset} size={human_size(p.size)} "
            f"first_lba={p.first_lba} last_lba={p.last_lba} fs={fs_name}"
        )
        for key, value in details.items():
            print(f"      {key}: {value}")


def print_scan_report(path: str, needles: list[bytes], contexts: bool) -> None:
    print("\nString scan")
    hits = scan_needles(path, needles)
    for needle in needles:
        label = needle.decode("utf-8", errors="replace")
        positions = hits[needle]
        print(f"  {label!r}: {len(positions)} hit(s)")
        if positions:
            print(f"      offsets: {', '.join(str(p) for p in positions[:10])}")
            if contexts:
                for pos in positions[:3]:
                    print(f"      context around {pos}:")
                    for ctx_offset, text in printable_context(path, pos):
                        squashed = text.replace("\r", "\\r").replace("\n", "\\n")
                        print(f"        {ctx_offset}: {squashed[:240]}")


def btrfs_partitions(path: str, partitions: list[Partition]) -> list[Partition]:
    result = []
    for partition in partitions:
        fs_name, _ = identify_filesystem(path, partition)
        if fs_name == "btrfs":
            result.append(partition)
    return result


def read_btrfs_file(path: str, partition: Partition, target_path: str) -> bytes:
    try:
        from dissect.btrfs import Btrfs
    except ImportError as exc:
        raise RuntimeError("install optional dependency: python -m pip install dissect.btrfs") from exc

    with OffsetReader(path, partition.offset, partition.size) as stream:
        fs = Btrfs(stream)
        inode = fs.get(target_path)
        with inode.open() as fh:
            return fh.read()


def print_btrfs_extract_report(path: str, partitions: list[Partition], targets: list[str]) -> None:
    if not targets:
        return

    print("\nBtrfs file extraction")
    candidates = btrfs_partitions(path, partitions)
    if not candidates:
        print("  no btrfs partition found")
        return

    for partition in candidates:
        print(f"  partition {partition.index}: {partition.name} offset={partition.offset}")
        for target_path in targets:
            print(f"    {target_path}:")
            try:
                data = read_btrfs_file(path, partition, target_path)
            except Exception as exc:  # noqa: BLE001 - this is a diagnostic tool.
                print(f"      unable to read: {exc}")
                if "zstandard" in str(exc).lower() or "zstd" in str(exc).lower():
                    print("      hint: python -m pip install 'dissect.btrfs[full]'")
                continue

            print(f"      size: {len(data)} bytes")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("utf-8", errors="replace")
            for line in text.splitlines():
                print(f"      | {line}")


def default_needles() -> list[bytes]:
    return [
        b"99-bypass-router",
        b"98-lucky-daji",
        b"lucky.daji",
        b"10.11.11.3",
        b"10.11.11.1",
        b"192.168.1.1",
        b"network.wan",
        b"network.lan",
        b"br-lan",
        b"config interface",
        b"option ipaddr",
        b"wxy-oect",
    ]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="For btrfs file extraction, install: python -m pip install 'dissect.btrfs[full]'",
    )
    parser.add_argument("image", help="path to a raw OpenWrt disk image")
    parser.add_argument(
        "--context",
        action="store_true",
        help="print nearby printable strings for the first few hits of each needle",
    )
    parser.add_argument(
        "--needle",
        action="append",
        default=[],
        help="extra ASCII/UTF-8 string to scan for; can be repeated",
    )
    parser.add_argument(
        "--extract",
        action="append",
        default=[],
        help="path to extract from btrfs rootfs when dissect.btrfs is installed; can be repeated",
    )
    parser.add_argument(
        "--no-default-extract",
        action="store_true",
        help="disable default btrfs extraction targets",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    image = os.path.abspath(args.image)
    if not os.path.isfile(image):
        print(f"image not found: {image}", file=sys.stderr)
        return 2

    print(f"Image: {image}")
    print(f"Size:  {human_size(os.path.getsize(image))}")

    try:
        partitions = parse_gpt(image)
    except ValueError as exc:
        print(f"Unable to parse GPT: {exc}", file=sys.stderr)
        return 1

    print_partition_report(image, partitions)

    needles = default_needles() + [needle.encode("utf-8") for needle in args.needle]
    print_scan_report(image, needles, args.context)

    extract_targets = [] if args.no_default_extract else ["/etc/config/network", "/etc/uci-defaults/99-bypass-router"]
    extract_targets.extend(args.extract)
    print_btrfs_extract_report(image, partitions, extract_targets)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
