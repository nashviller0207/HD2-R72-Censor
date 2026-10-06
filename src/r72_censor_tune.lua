-- HD2-Addon: mods/nashviller0207/r72_censor_tune
-- R-72 Censor ASVAL —— 数值调整(射速 / 穿甲)+ 射击模式扩展
--
-- 发布名:R-72 Censor ASVAL 1.1
-- 射速基准参考 AS Val 的 900 RPM,取整为 850 RPM。
--
-- 原版基线(来自 HD2Runtime PlayerWeaponAuthoringCapabilities.json,
-- game.dll 指纹 2E2C3B7C2500646DADD5F2B4C6E0504DBB7E7896139F64CDDC0D1813C718F51E):
--   weapon.fire_rate        400     (writeScope = weapon_local)
--   damage.ap_direct          2     (writeScope = shared_projectile_damage_definition)
--   damage.ap_slight          2     (同上)
--   damage.ap_large           2     (同上)
--   fire_mode.modes   ['single']    (writeScope = weapon_local)
--
-- 改动:
--   射速 400 -> 850
--   穿甲 2/2/2 -> 3/3/3(直射/小角度/大角度)
--   射击模式 ['single'] -> ['single','automatic']
--
-- v0.2 修正(实机反馈):
--   上一版把射速与三个穿甲字段放进同一个事务,而穿甲字段的 writeScope 是
--   shared_projectile_damage_definition,写入被拒:
--       "shared field requires allow_shared=true: damage.ap_direct"
--   事务是原子的 —— 一项被拒则整笔回滚,导致射速也一并失效。
--   现在拆成两笔独立操作:
--     1) 射速(weapon_local,不需要 allow_shared)
--     2) 穿甲(shared,显式声明 allow_shared=true)
--   这样一笔失败不会拖累另一笔。
--
-- 说明:
--   - 弹匣容量与数量不可改:该武器的生效值由默认改装配件(AddPath)拥有,
--     其覆盖记录未获批准写入。
--   - fire_mode.modes 需要 allow_unverified_effect:引擎的所有者、字节与
--     枚举含义均已证实,但"增删射击模式"未经实机游玩验证(已实测通过)。

local ok, hd2 = pcall(require, 'mods/skyeshade/hd2runtime')
if not ok or hd2 == nil then
    -- 缺少依赖时保持静默:应由加载器日志体现,而非报错刷屏
    return
end

local results = {}

-- 1) 射速:weapon_local,不需要 allow_shared
--    单独成笔,避免被其它字段的拒绝连带回滚
local ok1, r1 = pcall(hd2.ensure, {
    patch = {
        id = 'r72-censor-fire-rate',
        target = hd2.weapon('R-72 Censor'),
        field = hd2.fields.weapon.fire_rate,
        expect = 400,
        value = 850,
    },
})
results[#results + 1] = { name = 'fire_rate', ok = ok1, result = r1 }

-- 2) 穿甲三档:位于共享 DamageInfo 记录,必须显式 allow_shared=true
local ok2, r2 = pcall(hd2.ensure, {
    transaction = {
        id = 'r72-censor-ap',
        target = hd2.weapon('R-72 Censor'),
        allow_shared = true,
        changes = {
            { field = hd2.fields.damage.ap_direct, expect = 2, value = 3 },
            { field = hd2.fields.damage.ap_slight, expect = 2, value = 3 },
            { field = hd2.fields.damage.ap_large,  expect = 2, value = 3 },
        },
    },
})
results[#results + 1] = { name = 'armor_pen', ok = ok2, result = r2 }

-- 3) 射击模式:追加全自动(选择器已绑定,可在游戏中切换)
local ok3, r3 = pcall(hd2.ensure, {
    patch = {
        id = 'r72-censor-fire-modes',
        target = hd2.weapon('R-72 Censor'),
        field = hd2.fields.fire_mode.modes,
        expect = { 'single' },
        value = { 'single', 'automatic' },
        allow_unverified_effect = true,
    },
})
results[#results + 1] = { name = 'fire_modes', ok = ok3, result = r3 }

-- 汇总到独立日志,便于排查
local loader = rawget(_G, 'CowboyBingusModLoader')
local log = nil
if type(loader) == 'table' and type(loader.open_log) == 'function' then
    log = loader.open_log('R72CensorTune.log')
end
if log then
    pcall(function()
        log:write('R-72 Censor ASVAL v1.1\n')
        log:write('=========================\n')
        for _, item in ipairs(results) do
            log:write(string.format('[%s] pcall_ok=%s\n', item.name, tostring(item.ok)))
        end
        log:write('\n注:详细写入结果见 HD2Runtime.log\n')
        log:flush()
    end)
end

return results
