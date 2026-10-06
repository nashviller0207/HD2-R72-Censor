# R-72 Censor — 射速与射击模式调整

《绝地潜兵 2》(Helldivers 2)的 R-72 Censor 修改 mod。基于 [HD2Runtime](https://github.com/SkyeShade/HD2Runtime) 的语义化授权 API,带写入前基线校验。

**两个版本,任选其一。** 两者使用不同的资源名与 GUID,但**功能重叠**(都在射击模式里加全自动),**请勿同时启用**。

| 版本 | 射速 | 穿甲(直射/小角度/大角度) | 射击模式 | 下载 |
|---|---|---|---|---|
| **ASVAL** | 400 → **850** | 2/2/2 → **3/3/3** | 单发 → **单发 + 全自动** | [`R72-Censor-ASVAL-1.1.zip`](dist/R72-Censor-ASVAL-1.1.zip) |
| **Fire Modes** | **不变(400)** | **不变(2/2/2)** | 单发 → **单发 + 全自动** | [`R72-Censor-FireModes-1.0.zip`](dist/R72-Censor-FireModes-1.0.zip) |

> **ASVAL 版**的射速基准参考 **AS Val 的 900 RPM**(理论射速),取整为 850 RPM,同时把三档穿甲提到 3。
>
> **Fire Modes 版只动射击模式,不碰任何数值。** 适合只想要全自动、不想改变武器平衡的玩家。

---

## 前置依赖

**两个 mod 都必须同时安装以下两个前置。** mod 管理器不会自动装依赖。

| 依赖 | 版本要求 | 下载 |
|---|---|---|
| **Bingus Shared Loader** | **v15 或更新**(推荐 v19) | [Releases](https://github.com/CowboyBingus/BingusSharedLoader/releases) |
| **HD2Runtime** | **0.28.x**(推荐 0.28.1) | [Releases](https://github.com/SkyeShade/HD2Runtime/releases) |

## 安装

1. **关闭游戏。**
2. 用 **HD2 Arsenal** 或 **HD2 Mod Manager** 导入三个 ZIP:两个依赖 + 本 mod 的一个版本。
3. 全部启用,点 **Deploy**。
4. 启动游戏,进任务,**重新装备一次 R-72 Censor**。

### ⚠️ 加载顺序

**Bingus Shared Loader 必须排在加载顺序的最后**(Arsenal 默认优先级下放最底部;若启用 first-mod priority 则放最前)。

HD2Runtime 需要**排在 loader 之前**。

排错了不会报错,**只是静默不生效**。

## 生效时机

大部分字段在武器被**重新构建**后才生效。**已经在手上的枪保持旧属性**,直到它被重建 ——

> 重新部署、增援复活、或把枪换成别的再换回来。

所以装完 mod 后如果数值没变,**先重新装备一次**。

## 已知限制

| 限制 | 说明 |
|---|---|
| **弹匣容量与数量不可改** | R-72 Censor 的弹匣生效值由**默认改装配件(AddPath)**拥有,其覆盖记录不在 HD2Runtime 的可写范围内。容量、起始弹匣、备用弹匣、补给量全部只读。 |
| **穿甲需要 `allow_shared=true`** | 穿甲字段存放在共享的 `DamageInfo` 记录里(`shared_projectile_damage_definition`),即使当前只有本武器引用它,运行时仍要求显式授权。 |
| **射击模式需要 `allow_unverified_effect`** | 引擎的所有者、字节与枚举含义都已证实,但"增删射击模式"未经上游官方实机游玩验证。本 mod 已实机确认生效。 |
| **游戏更新后可能失效** | 运行时会校验游戏指纹。更新后若指纹不符,写入会被**拒绝**(而不是盲改),需等待 HD2Runtime 更新。 |

## 关于安全性

本 mod **不自己修改内存**。它只通过 HD2Runtime 提供的语义化 API 提交"字段 + 期望原值 + 新值",由运行时负责:

- 校验游戏指纹
- 比对当前值是否等于声明的原版基线(**不符则拒绝写入**,绝不盲目覆盖)
- 检查共享数据是否需要授权
- 写入后回读验证,并恢复内存页保护

**每笔改动都声明了 `expect` 基线值。** 如果游戏更新或其它 mod 已经改过该值,写入会被拒绝而不是盲改 —— 这也是为什么上游日志会明确写出 `rejected: <原因>`。

---

## 从源码构建

本仓库的 ZIP 是**可复现构建**(ZIP 内条目使用固定时间戳)。

```bash
cd tools
python build_r72_release.py
```

该脚本会先做**离线预检**(对照 HD2Runtime 能力目录逐条校验字段名、基线值、`allow_shared` 声明、射击模式能力),再编译校验 Lua 并打包。

依赖:`Python 3.10+`、`lupa`(`pip install lupa`)。

## 仓库结构

```
.
├─ src/
│  ├─ r72_censor_tune.lua          # Tune 版源码
│  └─ r72_censor_fire_modes.lua    # Fire Modes 版源码
├─ dist/                            # 发布包(ZIP)
├─ tools/
│  ├─ hd2pack.py                    # 打包器(MurmurHash64A + HD2 归档格式)
│  └─ build_r72_release.py          # 预检 + 构建
└─ README.md
```

## 打包格式说明

HD2 的 mod 本质是 `data/` 目录下的 `.patch_N` 归档,本次实现依据 loader 官方作者文档:

- 资源名须以 `-- HD2-Addon: mods/<作者>/<名称>` 的形式写在 Lua 首行(前 256 字节内,无 BOM)
- 归档内 Lua 载荷为 `<小端长度><版本 2><源码>` 的信封
- 资源哈希使用 **seed-zero MurmurHash64A**
- 发现机制读取 `data/9ba626afa44a3aa3.patch_<编号>`,**编号越大越先加载**

## 验证状态

| 项 | 状态 |
|---|---|
| 离线预检(字段名/基线/授权范围) | ✅ 通过 |
| LuaJIT 编译校验 | ✅ 通过 |
| 打包格式 | ✅ 归档头、资源哈希、载荷全部逐字节校验 |
| **实机验证** | ✅ **已确认**:射速、穿甲、射击模式三项均生效 |

游戏构建:**`1.8.46015.0` / Steam buildid `25480438`**
`game.dll` SHA256:`2E2C3B7C2500646DADD5F2B4C6E0504DBB7E7896139F64CDDC0D1813C718F51E`

## 致谢

- [Bingus Shared Loader](https://github.com/CowboyBingus/BingusSharedLoader) — CowboyBingus,提供 addon 加载与发现机制
- [HD2Runtime](https://github.com/SkyeShade/HD2Runtime) — SkyeShade,提供带防护的语义化写入 API
- [FileDiver](https://github.com/xypwn/filediver) — xypwn,文件格式研究

## 许可

MIT,见 [LICENSE](LICENSE)。

本项目为**客户端 mod**,不修改游戏文件、不注入进程、不提供任何多人游戏优势 —— 它改变的字段由本地客户端拥有,与外观类 mod 属同一加载路径。
