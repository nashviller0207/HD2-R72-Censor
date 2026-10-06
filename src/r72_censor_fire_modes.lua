-- HD2-Addon: mods/nashviller0207/r72_censor_fire_modes
-- R-72 Censor —— 射击模式扩展(仅此一项,不改动任何数值)
--
-- 原版基线(HD2Runtime PlayerWeaponAuthoringCapabilities.json,
-- game.dll 指纹 2E2C3B7C2500646DADD5F2B4C6E0504DBB7E7896139F64CDDC0D1813C718F51E):
--   fire_mode.modes = ['single']   (writeScope = weapon_local)
--   武器能力:state=selectable, selectorBound=true, maxModes=4, writable=true
--
-- 改动:
--   射击模式 ['single'] -> ['single','automatic']
--   模式选择器已由游戏绑定,因此可在游戏中自由切换单发 / 全自动。
--   该改动不触碰射速、伤害、穿甲、弹道、弹匣中的任何一项。
--
-- 说明:
--   fire_mode.modes 需要 allow_unverified_effect=true:引擎的所有者、字节与
--   枚举含义均已证实,但"增删射击模式"未经官方实机游玩验证。
--   (本 mod 作者已实机确认生效。)
--
--   allow_shared 不需要:weapon_local 作用域,该记录只有本武器一个所有者。

local ok, hd2 = pcall(require, 'mods/skyeshade/hd2runtime')
if not ok or hd2 == nil then
    -- 缺少依赖时保持静默:应由加载器日志体现,而非报错刷屏
    return
end

local results = {}

local ok1, r1 = pcall(hd2.ensure, {
    patch = {
        id = 'r72-censor-fire-modes-only',
        target = hd2.weapon('R-72 Censor'),
        field = hd2.fields.fire_mode.modes,
        expect = { 'single' },
        value = { 'single', 'automatic' },
        allow_unverified_effect = true,
    },
})
results[#results + 1] = { name = 'fire_modes', ok = ok1, result = r1 }

local loader = rawget(_G, 'CowboyBingusModLoader')
local log = nil
if type(loader) == 'table' and type(loader.open_log) == 'function' then
    log = loader.open_log('R72CensorFireModes.log')
end
if log then
    pcall(function()
        log:write('R-72 Censor Fire Modes\n')
        log:write('======================\n')
        for _, item in ipairs(results) do
            log:write(string.format('[%s] pcall_ok=%s\n', item.name, tostring(item.ok)))
        end
        log:write('\n注:详细写入结果见 HD2Runtime.log\n')
        log:flush()
    end)
end

return results
