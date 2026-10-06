"""
HD2 addon 打包器 — 复现 Samurai019/HD2-Target-Overlay 的归档格式。

来源参考:ref-overlay/build.py(同作者,已验证可在游戏中加载)

格式要点:
  - 资源哈希 = MurmurHash64A
  - 归档头: 魔数 0xf0000011
  - 偏移 72:  <IIQIIII  = (0, 0, 0xa14e8dfa2cd117e2, 1, 0, 16, 16)
  - 偏移 104: <7Q6I     = (resource_hash, 0xa14e8dfa2cd117e2, offset, 0,0,0,0, len, 0,0,16,16,0)
  - 偏移 192: payload = <II(len(src), 2)> + src
  - Lua 源码首行必须为: -- HD2-Addon: mods/<作者>/<mod名>

本模块只做打包,不修改游戏安装目录。
"""
import json
import struct
import zipfile
import hashlib
import re
from pathlib import Path

MAGIC = 0xF0000011
RES_TYPE = 0xA14E8DFA2CD117E2
ADDON_MARKER = b"-- HD2-Addon: "
ARCHIVE_STEM = "9ba626afa44a3aa3"


def resource_hash(name: str) -> int:
    """HD2 资源名哈希 = MurmurHash64A(与 ref-overlay/build.py 逐字一致)。"""
    data = name.encode()
    mask = (1 << 64) - 1
    mix = 0xC6A4A7935BD1E995
    value = len(data) * mix & mask
    end = len(data) // 8 * 8
    for (word,) in struct.iter_unpack("<Q", data[:end]):
        word = word * mix & mask
        word ^= word >> 47
        value = (value ^ (word * mix & mask)) * mix & mask
    if data[end:]:
        value = (value ^ int.from_bytes(data[end:], "little")) * mix & mask
    value ^= value >> 47
    value = value * mix & mask
    return value ^ (value >> 47)


def build_archive(source: bytes, resource_name: str) -> bytes:
    """把 Lua 源码包成 HD2 归档字节流。"""
    if not source.startswith(ADDON_MARKER + resource_name.encode()):
        raise ValueError(
            "Lua 源码首行必须是 '-- HD2-Addon: %s'" % resource_name
        )
    payload = struct.pack("<II", len(source), 2) + source
    offset = 192
    total = (offset + len(payload) + 15) & ~15

    data = bytearray(total)
    struct.pack_into("<III20sQQ24s", data, 0, MAGIC, 1, 1, b"", total, 0, b"")
    struct.pack_into("<IIQIIII", data, 72, 0, 0, RES_TYPE, 1, 0, 16, 16)
    struct.pack_into(
        "<7Q6I", data, 104,
        resource_hash(resource_name), RES_TYPE, offset,
        0, 0, 0, 0, len(payload), 0, 0, 16, 16, 0,
    )
    data[offset:offset + len(payload)] = payload
    return bytes(data)


def verify_archive(archive: bytes, source: bytes) -> None:
    """读回校验:确认偏移 120 处的 offset 和偏移 160 处的 len 能取回原始源码。"""
    off = struct.unpack_from("<Q", archive, 120)[0]
    length = struct.unpack_from("<I", archive, 160)[0]
    got = archive[off + 8:off + length]
    assert got == source, "归档往返校验失败"


def _safe(text: str) -> str:
    assert text.isascii(), "manifest 字段必须为 ASCII: %r" % text
    assert not re.search(r'[\\/:*?"<>|]', text), "非法字符: %r" % text
    return text


def build_zip(
    source: bytes,
    resource_name: str,
    title: str,
    description: str,
    guid: str,
    dest: Path,
    readme: bytes = b"",
) -> Path:
    """产出可被 Arsenal / HD2MM 导入的 ZIP。

    ZIP 内所有条目使用固定时间戳,使构建结果可复现
    (否则每次构建的容器哈希都会变,无法做哈希校验)。
    注意:归档字节本身一直是确定的,时间戳只影响 ZIP 容器。
    """
    archive = build_archive(source, resource_name)
    verify_archive(archive, source)

    manifest = {
        "Version": 1,
        "Guid": guid,
        "Name": _safe(title),
        "Description": _safe(description),
        "Options": [
            {"Name": title, "Description": description, "Include": ["Addon"]}
        ],
    }

    # 固定时间戳(1980-01-01, ZIP 纪元最小值),保证可复现构建
    FIXED_DATE = (1980, 1, 1, 0, 0, 0)

    def write(z, name, body):
        info = zipfile.ZipInfo(filename=name, date_time=FIXED_DATE)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o600 << 16   # 常规文件权限
        z.writestr(info, body)

    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w") as z:
        write(z, "manifest.json", json.dumps(manifest, indent=2).encode())
        write(z, "Addon/%s.patch_0" % ARCHIVE_STEM, archive)
        write(z, "Addon/%s.patch_0.stream" % ARCHIVE_STEM, b"")
        write(z, "Addon/%s.patch_0.gpu_resources" % ARCHIVE_STEM, b"")
        if readme:
            write(z, "README.md", readme)

    # 独立校验生成的 ZIP 自身完好
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        verify_archive(z.read("Addon/%s.patch_0" % ARCHIVE_STEM), source)

    return dest


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
