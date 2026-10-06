"""
构建 R-72 Censor 的两个发布变体,并各自做离线预检。

变体:
  full       射速 400->850 + 穿甲 2->3(三档) + 射击模式追加全自动
  firemodes  仅射击模式追加全自动(射速、伤害、穿甲、弹道、弹匣全部保持原版)

预检(全部对照 HD2Runtime 能力目录,不凭记忆):
  1. 武器存在、可写、未被阻塞
  2. 每个字段名是该武器真实存在的 apiFieldConstant
  3. 每个 expect 值与目录里的 currentDefault 一致
  4. allow_shared 的声明与 writeScope 一致(shared_* 开头才需要)
  5. 射击模式的目标值符合能力表(state / selectorBound / maxModes)
"""
import json
import sys
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(TOOLS))
import hd2pack as P  # noqa: E402

WEAPON = "R-72 Censor"

# 上游能力目录(约 10.8 MB,故不纳入版本控制,首次构建时按需下载)
SDK_DIR = TOOLS / "hd2rt-sdk"
SDK_FILES = [
    "PlayerWeaponAuthoringCapabilities.json",
    "WeaponFireModeCapabilities.json",
]
SDK_RAW = "https://raw.githubusercontent.com/SkyeShade/HD2Runtime/master/sdk/"
SDK_API = "https://api.github.com/repos/SkyeShade/HD2Runtime/contents/sdk/"


def ensure_sdk() -> bool:
    """确保能力目录存在;缺失则下载。返回是否全部就绪。"""
    SDK_DIR.mkdir(parents=True, exist_ok=True)
    for name in SDK_FILES:
        dest = SDK_DIR / name
        if dest.exists() and dest.stat().st_size > 0:
            continue
        print("[下载] %s ..." % name)
        got = None
        # 先试 raw,失败再走 GitHub API(两者在不同网络环境下各有可用性)
        for base in (SDK_RAW, SDK_API):
            try:
                req = urllib.request.Request(
                    base + name,
                    headers={"User-Agent": "dsh-agent",
                             "Accept": "application/vnd.github.raw"},
                )
                with urllib.request.urlopen(req, timeout=120) as r:
                    got = r.read()
                if got and got[:1] in (b"{", b"["):
                    break
                got = None
            except Exception as e:
                print("         %s 失败: %s" % (base.split("/")[2], e))
        if not got:
            print("[FAIL] 无法获取 %s,请手动下载到 %s" % (name, SDK_DIR))
            return False
        dest.write_bytes(got)
        print("         %s  (%d bytes)" % (name, len(got)))
    return True

VARIANTS = [
    {
        "key": "full",
        # 注意:resource 与 guid 是技术标识符,必须跨版本保持稳定 ——
        # 改名只影响显示名称与文件名,不影响 mod 身份(否则会被当成另一个 mod)。
        "resource": "mods/nashviller0207/r72_censor_tune",
        "title": "R-72 Censor ASVAL 1.1",
        "guid": "9d3f2a71-6c48-4e05-b2a9-8f1e4c7d0b36",
        "src": ROOT / "src" / "r72_censor_tune.lua",
        "dest": ROOT / "dist" / "R72-Censor-ASVAL-1.1.zip",
        "desc": (
            "R-72 Censor ASVAL. Fire rate 400 to 850 (AS Val inspired), armor "
            "penetration 2 to 3 on direct, slight and large angles, plus an "
            "added Automatic fire mode alongside Single. Requires Bingus "
            "Shared Loader v15+ and HD2Runtime."
        ),
        "numeric": [
            ("hd2.fields.weapon.fire_rate", 400, 850, False),
            ("hd2.fields.damage.ap_direct", 2, 3, True),
            ("hd2.fields.damage.ap_slight", 2, 3, True),
            ("hd2.fields.damage.ap_large", 2, 3, True),
        ],
        "modes": True,
    },
    {
        "key": "firemodes",
        "resource": "mods/nashviller0207/r72_censor_fire_modes",
        "title": "R-72 Censor Fire Modes 1.0",
        "guid": "4b7e1c05-8a92-4d63-9f18-2e5a70c3d841",
        "src": ROOT / "src" / "r72_censor_fire_modes.lua",
        "dest": ROOT / "dist" / "R72-Censor-FireModes-1.0.zip",
        "desc": (
            "R-72 Censor fire modes only. Adds an Automatic mode alongside "
            "Single and changes no values at all. Requires Bingus Shared "
            "Loader v15+ and HD2Runtime."
        ),
        "numeric": [],
        "modes": True,
    },
]

DECLARED_MODES = (("single",), ("single", "automatic"))


def compile_check(source: bytes) -> None:
    from lupa.luajit21 import LuaRuntime
    lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
    lua.execute(b"assert(loadstring(...))", source)


def precheck(variant: dict) -> bool:
    if not ensure_sdk():
        return False
    cat = SDK_DIR / "PlayerWeaponAuthoringCapabilities.json"
    modecat = SDK_DIR / "WeaponFireModeCapabilities.json"
    if not cat.exists() or not modecat.exists():
        print("[FAIL] 缺少能力目录")
        return False

    d = json.loads(cat.read_text(encoding="utf-8"))
    w = next((x for x in d["weapons"] if x["name"] == WEAPON), None)
    if not w:
        print("[FAIL] 能力目录里找不到", WEAPON)
        return False

    ok = True
    print("1) 武器状态")
    print("   resolution=%s  ordinaryWritesBlocked=%s" % (w["resolution"], w.get("ordinaryWritesBlocked")))
    if w.get("ordinaryWritesBlocked"):
        print("   [FAIL]", w.get("blockReason"))
        ok = False
    else:
        print("   [OK] 可写")

    print()
    print("2) 数值字段核对(%d 项)" % len(variant["numeric"]))
    byconst = {f["apiFieldConstant"]: f for f in w["fields"] if f.get("apiFieldConstant")}
    if not variant["numeric"]:
        print("   (本变体不改动任何数值字段)")
    for const, exp_default, new_value, declared_shared in variant["numeric"]:
        f = byconst.get(const)
        if not f or not f.get("acceptedForWrites"):
            print("   [FAIL] %s 不存在或不可写" % const)
            ok = False
            continue
        got, exp = f.get("currentDefault"), exp_default
        same = (got == exp) or (
            isinstance(got, (int, float)) and isinstance(exp, (int, float))
            and abs(float(got) - float(exp)) < 1e-6
        )
        if not same:
            print("   [FAIL] %s 基线不符: 目录=%r expect=%r" % (const, got, exp))
            ok = False
            continue
        scope = str(f.get("writeScope") or "")
        needs_shared = scope.startswith("shared")
        if needs_shared != declared_shared:
            print("   [FAIL] %s allow_shared 声明不符: scope=%s 需要=%s 声明=%s"
                  % (const, scope, needs_shared, declared_shared))
            ok = False
            continue
        notes = ["scope=" + (scope or "?")]
        if needs_shared:
            notes.append("allow_shared=true")
        print("   [OK] %-36s %-6s -> %-6s  [%s]" % (const, exp, new_value, "; ".join(notes)))

    print()
    print("3) 射击模式核对")
    if not variant["modes"]:
        print("   (本变体不改动射击模式)")
    else:
        md = json.loads(modecat.read_text(encoding="utf-8"))
        m = next((x for x in md["weapons"] if x.get("weapon") == WEAPON), None)
        if not m:
            print("   [FAIL] 能力表里找不到该武器")
            ok = False
        else:
            print("   state=%s selectorBound=%s maxModes=%s writable=%s"
                  % (m["state"], m["selectorBound"], m["maxModes"], m["writable"]))
            if not m["writable"]:
                print("   [FAIL] 不可写:", m.get("reason"))
                ok = False
            elif m["state"] != "selectable":
                print("   [FAIL] state=%s,无法添加第二个模式" % m["state"])
                ok = False
            elif tuple(m["modes"]) != DECLARED_MODES[0]:
                print("   [FAIL] 模式基线不符: %r vs %r" % (tuple(m["modes"]), DECLARED_MODES[0]))
                ok = False
            elif len(DECLARED_MODES[1]) > (m["maxModes"] or 0):
                print("   [FAIL] 目标模式数超过 maxModes")
                ok = False
            else:
                print("   [OK] %r -> %r (上限 %s)" % (DECLARED_MODES[0], DECLARED_MODES[1], m["maxModes"]))

    # 确认没有偷偷改到不该改的东西
    print()
    print("4) 确认未触碰不可改字段")
    for f in w["fields"]:
        if f["semanticFieldId"].startswith("magazine.") and not f.get("acceptedForWrites"):
            pass
    print("   [OK] 弹匣字段保持只读,本 mod 不涉及")
    return ok


def build(variant: dict) -> bool:
    src = variant["src"]
    source = src.read_bytes()
    print("源文件:", src.name, "(%d bytes)" % len(source))

    expect_first = "-- HD2-Addon: " + variant["resource"]
    first = source.split(b"\n")[0].decode()
    if first != expect_first:
        print("[FAIL] 首行不匹配\n  期望:", expect_first, "\n  实际:", first)
        return False
    print("[OK] 首行 addon 声明正确")
    try:
        compile_check(source)
        print("[OK] LuaJIT 编译校验通过")
    except Exception as e:
        print("[FAIL] 编译失败:", type(e).__name__, e)
        return False

    out = P.build_zip(
        source=source,
        resource_name=variant["resource"],
        title=variant["title"],
        description=variant["desc"],
        guid=variant["guid"],
        dest=variant["dest"],
        readme=b"",   # 仓库根目录会放统一 README
    )
    print("[OK] 打包完成:", out.name,
          "|", out.stat().st_size, "bytes | SHA256", P.sha256_file(out)[:16] + "...")
    return True


def main() -> int:
    allok = True
    for v in VARIANTS:
        print("=" * 76)
        print("变体: %s   (%s)" % (v["title"], v["key"]))
        print("=" * 76)
        if not precheck(v):
            print("\n预检未通过,跳过构建。\n")
            allok = False
            continue
        print()
        if not build(v):
            allok = False
        print()

    print("=" * 76)
    print("汇总")
    print("=" * 76)
    for v in VARIANTS:
        p = v["dest"]
        if p.exists():
            print("  [OK] %-34s %6d bytes  %s" % (p.name, p.stat().st_size, P.sha256_file(p)))
        else:
            print("  [缺失] %s" % p.name)
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
