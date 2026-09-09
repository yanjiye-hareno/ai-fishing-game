#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""釣魚進度看板產生器 —— 讀存檔 + 引擎資料表，吐一支單檔 HTML。

    python dashboard/generate_dashboard.py

產物：dashboard/index.html（零外部依賴、深色像素風、手機可看）。

【防劇透設計（本檔最高規格）】
玩家是盲玩的：他不知道還沒收錄的物種有哪些。因此本腳本與產物遵守——
  1. 未收錄的格子只輸出「編號 + ???」，名稱 / 稀有度 / 描述 / 棲地一律不寫進 HTML
     （是「根本不寫」，不是用 CSS 藏起來）。
  2. 未解鎖釣點只輸出「??? + 解鎖點數」（點數在遊戲商店本來就看得到）。
  3. 圖鑑格子的編號用 id 的 SHA-1 排序打散——若照引擎原始順序排，未收錄格子的
     位置會反推出稀有度分布，等於間接劇透。
  4. 進度只給總數，不給各稀有度的分母（分母會洩漏「還有幾種沒收」的結構）。
  5. 本檔程式碼與註解不出現任何物種名稱，全部從引擎動態讀取。
  6. 像素圖示只對「存檔裡已收錄」的物種生成；未收錄一律共用同一枚問號圖示，
     不畫各自剪影——體型輪廓本身也是線索。
"""

import hashlib
import html
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.dirname(HERE)
ENGINE_PATH = os.path.join(GAME_DIR, "engine.py")
SAVE_PATH = os.path.join(GAME_DIR, "fishing_save.json")
OUT_PATH = os.path.join(HERE, "index.html")

TW = timezone(timedelta(hours=8))

# 稀有度 → 配色（key 對應引擎的稀有度鍵；不含任何物種資訊）
RARITY_COLOR = {
    "common": "#8fa3b0",
    "uncommon": "#5fd07a",
    "rare": "#4fa8ff",
    "epic": "#b478ff",
    "legendary": "#ffa63d",
    "mythic": "#ff5fa2",
}
FALLBACK_COLOR = "#8fa3b0"


def load_engine_tables():
    """把 engine.py 讀進獨立命名空間取資料表。

    唯讀：引擎的頂層只有資料定義，沒有任何檔案 I/O；並關掉 bytecode 寫出，
    確保不在遊戲目錄留下任何新檔案。
    """
    sys.dont_write_bytecode = True
    with io.open(ENGINE_PATH, encoding="utf-8") as fh:
        src = fh.read()
    ns = {"__name__": "_dashboard_engine_view", "__file__": ENGINE_PATH}
    exec(compile(src, ENGINE_PATH, "exec"), ns)  # noqa: S102 - 唯讀取資料表
    return ns


def load_save():
    with io.open(SAVE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def save_stamp():
    """存檔檔案的修改時間（台北時間）。用檔案時間而非當下時間，讓重跑結果一致。"""
    return datetime.fromtimestamp(os.path.getmtime(SAVE_PATH), TW).strftime("%y-%m-%d %H:%M")


def frags_needed(loc):
    """該釣點拼齊藏寶圖所需碎片數（與引擎同一條規則）。"""
    cost = loc.get("unlock_cost", 0)
    return 3 if cost <= 200 else (4 if cost <= 480 else 5)


def esc(text):
    return html.escape(str(text), quote=True)


def slot_order(fish_table):
    """穩定但與稀有度無關的格子順序：照 id 的 SHA-1 排。"""
    return sorted(fish_table.keys(), key=lambda k: hashlib.sha1(k.encode("utf-8")).hexdigest())


def fmt_size(value):
    if value is None:
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return esc(value)
    return ("%.1f" % num).rstrip("0").rstrip(".")


# ────────────────────────── 像素圖示 ──────────────────────────
#
# 【防劇透】本節兩張對照表（形態、色相）只收「目前已收錄物種身上出現過的
# 字與標籤」；沒命中就走通用款，所以表本身不含任何未收錄物種的資訊，日後
# 收錄新物種也不需要改碼。未收錄的格子根本不會走進這裡——它們共用一枚寫死
# 的問號圖示。
#
# 畫布 14×10，輸出時放大整數 2 倍（28×20 CSS px）＋ shape-rendering:crispEdges，
# 邊緣才會硬、不糊。字元：o 描邊/暗部、b 主色、l 高光、a 稀有度強調色、
# e 眼睛、d 暗色（問號／鎖）、. 透明。

PX_W = 14
PX_H = 10

SHAPES = {
    # 通用魚形（沒命中形態表的一律走這張）
    "fish": (
        ".....aa.......",
        "...aaoooo.....",
        "..obbbbbbo.oo.",
        ".obbllbbbbboa.",
        "obeblllbbbbbba",
        "obeblllbbbbbba",
        ".obbllbbbbboa.",
        "..obbbbbbo.oo.",
        "...aaoooo.....",
        ".....aa.......",
    ),
    "eel": (
        "...........aaa",
        "........ooaao.",
        ".....ooobblo..",
        "...oobbbblo...",
        ".oobbbbblo....",
        "obebbbbblo....",
        ".oobbbbbblo...",
        "...ooooooo....",
        "..............",
        "..............",
    ),
    "ray": (
        "..............",
        "...oooo.......",
        "..obbbbo......",
        ".obbbbbbo.....",
        "obebbbbbbo....",
        "obebllbbbboaaa",
        ".obbbbbbo.....",
        "..obbbbo......",
        "...oooo.......",
        "..............",
    ),
    "shrimp": (
        "a.............",
        ".aa...........",
        "...oooooo.....",
        "..obbbbbbbo...",
        ".obebbllbbbbo.",
        ".obbbbbbbbbboa",
        "..obbbbbbbbo.a",
        "...oaoaoaoo.a.",
        "....a.a.a.....",
        "..............",
    ),
    "snail": (
        ".....oooo.....",
        "...oobbbboo...",
        "..obblllbbbo..",
        "..obloooolbo..",
        "..oblobbolbo..",
        "..obbloollbo..",
        "...oobbbbboo..",
        "aa..oobbbboo..",
        ".aaoaaaaaaaao.",
        "..............",
    ),
    "catfish": (
        "..............",
        "......ooo.....",
        "..ooobbbboo.oo",
        ".obbbbbbbbbooo",
        "obeblbbbbbbboo",
        "obeblbbbbbbboo",
        ".obbbbbbbbbooo",
        "aaoobbbbboo.oo",
        ".aa...ooo.....",
        "..............",
    ),
    "newt": (
        "..............",
        "..............",
        "...oooo.......",
        "..obbbboooo...",
        "obebbbbbbbbboo",
        "obebbllbbbbboo",
        ".obbbbbbbbbbo.",
        "..oao....oao..",
        "..a.a....a.a..",
        "..............",
    ),
    "wyrm": (
        "aa.aa.........",
        ".aoooa........",
        "obebbbo.......",
        "obbbllbo......",
        ".oobbbbboo....",
        "...oobbbbbbo..",
        ".....oobbbbbo.",
        ".......obbbbbo",
        "........oobboa",
        "...........aaa",
    ),
    "puffer": (
        "..a...aa......",
        ".aoooobbooa...",
        "aobbbbbbbboa..",
        "obellbbbbbbbaa",
        "obebllbbbbbbba",
        "aobbbbbbbbboa.",
        ".aoobbbbbboa..",
        "..aooooooa.a..",
        "...a..aa......",
        "..............",
    ),
    # 未收錄專用：所有未收錄格子共用這一張，零差異
    "unknown": (
        "..............",
        "....dddd......",
        "...dd..dd.....",
        "........dd....",
        ".......dd.....",
        "......dd......",
        "......dd......",
        "..............",
        "......dd......",
        "..............",
    ),
    # 未解鎖釣點專用：共用同一枚鎖
    "lock": (
        "..............",
        ".....dddd.....",
        "....dd..dd....",
        "....dd..dd....",
        "..dddddddddd..",
        "..dddd..dddd..",
        "..dddd..dddd..",
        "..dddddddddd..",
        "..dddddddddd..",
        "..............",
    ),
    # 地形（只有已解鎖釣點會用到；沒命中走 water）
    "pond": (
        "..............",
        ".........aaa..",
        ".........aaaa.",
        ".........aaa..",
        "...bbbbbbbb...",
        ".bbbbbbbbbbbb.",
        "bbbllbbbbbbbbb",
        "bbbbbbbbllbbbb",
        ".bbbbbbbbbbbb.",
        "...bbbbbbbb...",
    ),
    "river": (
        "..aa..aa...aa.",
        "..a...a....a..",
        "..a...a....a..",
        "..a...a....a..",
        "bbbbbbbbbbbbbb",
        "bbllbbbbllbbbb",
        "bbbbbbbbbbbbbb",
        "bbbbllbbbbllbb",
        "bbbbbbbbbbbbbb",
        "bbllbbbbbbbbll",
    ),
    "falls": (
        "....l....l....",
        "...l.l..l.l...",
        "....l....l....",
        "....a.....a...",
        "...aa....aaa..",
        "..aaa....aaa..",
        "..aaa...aaaa..",
        ".bbbbbbbbbbbb.",
        "bbbllbbbbllbbb",
        ".bbbbbbbbbbbb.",
    ),
    "water": (
        "..............",
        "..............",
        "..............",
        "...ll....ll...",
        "bbbbbbbbbbbbbb",
        "bbllbbbbllbbbb",
        "bbbbbbbbbbbbbb",
        "bbbbllbbbbllbb",
        "bbbbbbbbbbbbbb",
        "bbllbbbbbbbbll",
    ),
}

# 形態對照：只收「已收錄物種名稱裡出現過的字」，其餘一律通用魚形。
SHAPE_BY_CHAR = (
    ("鰻鰍", "eel"),
    ("蝦", "shrimp"),
    ("蝸螺", "snail"),
    ("鯰", "catfish"),
    ("鰩", "ray"),
    ("螈", "newt"),
    ("龍", "wyrm"),
    ("魨", "puffer"),
)

# 地形對照：只收「已解鎖釣點名稱裡出現過的字」，其餘一律通用水面。
TERRAIN_BY_CHAR = (
    ("瀑泉", "falls"),
    ("塘池", "pond"),
    ("河", "river"),
)

# 標籤 → 色相族：(標籤, 基準色相, 飽和倍率, 允許的色相飄移)
# 只收「已收錄物種身上出現過的標籤」，照順序取第一個命中的；都沒命中就用
# id 雜湊決定色相（仍然穩定，同一個 id 每次長一樣）。
TAG_HUE = (
    ("fire", 12, 1.00, 26),
    ("crystal", 186, 0.95, 16),
    ("mineral", 46, 0.85, 18),
    ("fantasy", 288, 1.00, 20),
    ("nocturnal", 232, 0.95, 16),
    ("armored", 210, 0.55, 14),
    ("underwater", 199, 0.90, 18),
    ("freshwater", 140, 0.85, 30),
)

# 稀有度 → (飽和度, 明度) 基準，稀有的更亮更飽和
RARITY_TONE = {
    "common": (46, 50),
    "uncommon": (56, 53),
    "rare": (66, 56),
    "epic": (74, 59),
    "legendary": (82, 62),
    "mythic": (90, 66),
}
DEFAULT_TONE = (50, 52)

TERRAIN_PALETTE = {
    "pond": {"b": "#1d4f6b", "l": "#7fd8e8", "a": "#e8dfa8"},
    "river": {"b": "#1f5a58", "l": "#74d6c0", "a": "#7fae55"},
    "falls": {"b": "#2a4f68", "l": "#ffc98f", "a": "#dff0ff"},
    "water": {"b": "#1d4f6b", "l": "#6fc7de", "a": "#6fc7de"},
}
LOCK_INK = "#2b4a63"
# 未收錄問號：本體壓暗、右下描一圈微亮刻痕，做成「凹進去的空插槽」。
# 58 格同時鋪開時，平塗的高對比會變成一片噪點；有層次但低對比才安靜。
UNKNOWN_INK = "#1c3245"
UNKNOWN_EDGE = "#2c4c68"


PX_CHARS = set(".oblmaed")


def _check_shapes():
    for key, rows in SHAPES.items():
        if len(rows) != PX_H:
            raise ValueError("圖形 %s 應有 %d 列，實際 %d" % (key, PX_H, len(rows)))
        for i, row in enumerate(rows):
            if len(row) != PX_W:
                raise ValueError("圖形 %s 第 %d 列寬 %d，應為 %d" % (key, i, len(row), PX_W))
            bad = set(row) - PX_CHARS
            if bad:
                raise ValueError("圖形 %s 第 %d 列有非法字元 %r" % (key, i, sorted(bad)))


_check_shapes()


def _hash_bytes(text):
    """id → 一串穩定的整數（不用 random，重跑結果永遠一樣）。"""
    return list(bytearray(hashlib.sha1(text.encode("utf-8")).digest()))


def _hsl_hex(hue, sat, lum):
    hue = float(hue) % 360.0
    sat = max(0.0, min(100.0, float(sat))) / 100.0
    lum = max(0.0, min(100.0, float(lum))) / 100.0
    c = (1.0 - abs(2.0 * lum - 1.0)) * sat
    x = c * (1.0 - abs((hue / 60.0) % 2.0 - 1.0))
    m = lum - c / 2.0
    seg = int(hue // 60) % 6
    rgb = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][seg]
    return "#%02x%02x%02x" % tuple(int(round((v + m) * 255)) for v in rgb)


def _shape_for(name):
    for chars, shape in SHAPE_BY_CHAR:
        for ch in chars:
            if ch in name:
                return shape
    return "fish"


def _terrain_for(name):
    for chars, shape in TERRAIN_BY_CHAR:
        for ch in chars:
            if ch in name:
                return shape
    return "water"


def _fish_palette(fid, tags, rarity):
    hv = _hash_bytes(fid)
    hue = None
    sat_mult = 1.0
    for tag, base_hue, mult, spread in TAG_HUE:
        if tag in tags:
            hue = (base_hue + (hv[0] % (2 * spread + 1)) - spread) % 360
            sat_mult = mult
            break
    if hue is None:
        hue = (hv[0] * 360 // 256) % 360
    sat, lum = RARITY_TONE.get(rarity, DEFAULT_TONE)
    sat = sat * sat_mult
    lum = lum + (hv[1] % 7) - 3
    # 眼睛跟著主色明暗反轉：主色夠亮就用暗瞳，主色本身很暗就改亮瞳，
    # 否則暗系的魚在深色底板上會被看成「頭上破了一個洞」。
    if lum >= 46:
        eye = _hsl_hex(hue, min(100, sat + 20), max(8, lum - 36))
    else:
        eye = _hsl_hex(hue - 12, max(0, sat - 26), min(94, lum + 34))
    return {
        "o": _hsl_hex(hue - 6, min(100, sat + 12), max(10, lum - 26)),
        "b": _hsl_hex(hue, sat, lum),
        "m": _hsl_hex(hue - 4, max(0, sat - 8), min(92, lum + 14)),
        "l": _hsl_hex(hue - 10, max(0, sat - 14), min(94, lum + 20)),
        "a": RARITY_COLOR.get(rarity, FALLBACK_COLOR),
        "e": eye,
    }


def _apply_pattern(rows, fid):
    """依 id 決定花紋（無／斜紋／點斑），只把主色格換成鄰近的中間色。

    刻意用中間色而不是高光色：對比拉太大會把輪廓切碎，小圖示會看不出形狀。
    """
    hv = _hash_bytes(fid)
    mode = hv[2] % 3
    if mode == 0:
        return rows
    off = hv[3] % 5
    out = []
    for y, row in enumerate(rows):
        chars = list(row)
        for x, ch in enumerate(chars):
            if ch != "b":
                continue
            if mode == 1 and (x + y + off) % 5 == 0:
                chars[x] = "m"
            elif mode == 2 and (x + off) % 3 == 1 and (y + off) % 3 == 1:
                chars[x] = "m"
        out.append("".join(chars))
    return out


def _rects(rows, ch):
    """把某個字元的格子壓成最少的矩形：先併同列橫向，再併上下同寬的。"""
    runs = []  # (y, x, w)
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] == ch:
                w = 0
                while x + w < len(row) and row[x + w] == ch:
                    w += 1
                runs.append([y, x, w, 1])
                x += w
            else:
                x += 1
    merged = []
    for run in runs:
        for prev in merged:
            if prev[1] == run[1] and prev[2] == run[2] and prev[0] + prev[3] == run[0]:
                prev[3] += 1
                break
        else:
            merged.append(run)
    return merged


def _svg_body(rows, colors):
    parts = []
    for ch in sorted(set("".join(rows)) - {"."}):
        color = colors.get(ch)
        if not color:
            continue
        d = "".join(
            "M%d %dh%dv%dH%dz" % (x, y, w, h, x) for y, x, w, h in _rects(rows, ch)
        )
        if d:
            parts.append('<path fill="%s" d="%s"/>' % (color, d))
    return "".join(parts)


def px_icon(rows, colors, extra_class=""):
    cls = "pxi" + (" " + extra_class if extra_class else "")
    return '<svg class="%s" viewBox="0 0 %d %d" aria-hidden="true">%s</svg>' % (
        cls, PX_W, PX_H, _svg_body(rows, colors),
    )


def fish_icon(fish):
    """已收錄物種的小圖示：形態看名稱、配色看標籤＋稀有度、花紋看 id 雜湊。"""
    fid = fish.get("id", "")
    rows = _apply_pattern(list(SHAPES[_shape_for(fish.get("name", ""))]), fid)
    return px_icon(rows, _fish_palette(fid, set(fish.get("tags", []) or []), fish.get("rarity", "")))


def _emboss(rows, body="d", edge="l"):
    """在右緣描一道亮邊，做出刻痕般的立體感（單色圖示專用）。

    只往右不往下：往下會把筆畫之間的留白填掉，問號的點就跟豎黏成一塊。
    """
    out = [list(r) for r in rows]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == body and x + 1 < PX_W and row[x + 1] != body:
                out[y][x + 1] = edge
    return ["".join(r) for r in out]


def unknown_icon():
    """未收錄格子共用——所有格子輸出完全一樣的字串。"""
    return px_icon(
        _emboss(SHAPES["unknown"]),
        {"d": UNKNOWN_INK, "l": UNKNOWN_EDGE},
        "px-unknown",
    )


def terrain_icon(name):
    shape = _terrain_for(name)
    return px_icon(SHAPES[shape], TERRAIN_PALETTE[shape], "px-loc")


def lock_icon():
    return px_icon(SHAPES["lock"], {"d": LOCK_INK}, "px-loc px-lock")


# ────────────────────────── 分頁：圖鑑 ──────────────────────────

def build_dex(fish_table, rarity_table, enc):
    order = slot_order(fish_table)
    total = len(order)
    got = sum(1 for fid in order if fid in enc)

    # 已收錄的稀有度計數（只給分子，不給分母——分母會洩漏未收錄結構）
    tally = {}
    for fid in order:
        if fid in enc:
            key = fish_table[fid].get("rarity", "")
            tally[key] = tally.get(key, 0) + 1
    chips = []
    for key, meta in rarity_table.items():
        if tally.get(key):
            chips.append(
                '<span class="chip" style="--c:%s">%s <b>%d</b></span>'
                % (RARITY_COLOR.get(key, FALLBACK_COLOR), esc(meta.get("label", key)), tally[key])
            )

    pct = int(round(got * 100.0 / total)) if total else 0
    bars = "".join(
        '<i class="%s"></i>' % ("on" if (i * total) < (got * 24) else "off") for i in range(24)
    )

    unknown = unknown_icon()  # 只算一次，63 格共用同一份字串
    cells = []
    for idx, fid in enumerate(order, start=1):
        num = "%02d" % idx
        rec = enc.get(fid)
        if not rec:
            # 未收錄：編號 + 統一問號圖示，不寫入任何來自引擎的欄位。
            # 圖示對每一格都完全相同——各自剪影會洩漏體型。
            cells.append(
                '<div class="cell locked"><div class="num">#%s</div>%s'
                '<div class="lockedtag">未收錄</div></div>' % (num, unknown)
            )
            continue
        f = fish_table[fid]
        rarity = f.get("rarity", "")
        color = RARITY_COLOR.get(rarity, FALLBACK_COLOR)
        label = rarity_table.get(rarity, {}).get("label", rarity)
        tag = rarity_table.get(rarity, {}).get("tag", "")
        unit = f.get("size_unit", "cm")
        cells.append(
            '<div class="cell got" style="--c:%s">'
            '<div class="cellhead"><div class="num">#%s</div>%s</div>'
            '<div class="fname">%s</div>'
            '<div class="rar">%s<span class="tag">%s</span></div>'
            '<div class="stat"><span>最大</span><b>%s %s</b></div>'
            '<div class="stat"><span>捕獲</span><b>%d 次</b></div>'
            '<div class="stat"><span>初遇</span><b>第 %s 回合</b></div>'
            "</div>"
            % (
                color,
                num,
                fish_icon(f),
                esc(f.get("name", "")),
                esc(label),
                esc(tag),
                fmt_size(rec.get("max_size")),
                esc(unit),
                int(rec.get("count", 0) or 0),
                esc(rec.get("first_caught_turn", "?")),
            )
        )

    return """
    <div class="panelhead">
      <div class="ph-left">
        <div class="ph-title">圖鑑</div>
        <div class="ph-sub">已收錄 <b>%d</b> / %d 種</div>
      </div>
      <div class="ph-right">%s</div>
    </div>
    <div class="pbar" role="img" aria-label="圖鑑進度 %d%%">%s<em>%d%%</em></div>
    <div class="grid dex">%s</div>
    """ % (got, total, "".join(chips), pct, bars, pct, "".join(cells))


# ────────────────────────── 分頁：地圖 ──────────────────────────

def map_order(loc_table, save):
    """釣點排序：當前 → 已解鎖 → 未解鎖，同組再按解鎖點數。"""
    unlocked = list(save.get("unlocked_locations", []))
    current = save.get("location_id")
    return sorted(
        loc_table.values(),
        key=lambda l: (
            0 if l.get("id") == current else (1 if l.get("id") in unlocked else 2),
            l.get("unlock_cost", 0),
            l.get("id", ""),
        ),
    )


def masked_labels(loc_table, save):
    """未解鎖釣點的代號（地圖頁與背包頁共用同一套編號，避免同一代號指到不同地方）。"""
    unlocked = list(save.get("unlocked_locations", []))
    labels = {}
    no = 0
    for loc in map_order(loc_table, save):
        if loc.get("id") not in unlocked:
            no += 1
            labels[loc.get("id")] = '??? <small>祕境 %02d</small>' % no
    return labels


def build_map(loc_table, season_table, save):
    unlocked = list(save.get("unlocked_locations", []))
    current = save.get("location_id")
    dive_unlocked = list(save.get("dive_unlocked", []))
    frags = save.get("map_fragments", {}) or {}
    labels = masked_labels(loc_table, save)
    lock = lock_icon()  # 未解鎖釣點共用同一份字串

    rows = []
    for loc in map_order(loc_table, save):
        lid = loc.get("id")
        is_unlocked = lid in unlocked
        is_current = lid == current
        if not is_unlocked:
            # 未解鎖：名稱遮蔽，只留解鎖點數（商店本來就看得到）
            # 未解鎖：一律同一枚鎖圖示，不依釣點屬性變化
            rows.append(
                '<div class="cell loc locked">'
                '<div class="loc-top">%s'
                '<span class="loc-name">%s</span></div>'
                '<div class="loc-cost">%d 點解鎖</div>'
                "</div>" % (lock, labels[lid], int(loc.get("unlock_cost", 0) or 0))
            )
            continue

        seasons = "・".join(
            season_table.get(s, {}).get("name", s) for s in loc.get("available_seasons", [])
        )
        if lid in dive_unlocked:
            dive = '<span class="badge dive-on">🤿 潛水已解鎖</span>'
        else:
            need = frags_needed(loc)
            have = int(frags.get(lid, 0) or 0)
            pips = "".join(
                '<i class="%s"></i>' % ("on" if i < have else "off") for i in range(need)
            )
            dive = (
                '<span class="badge dive-off">🧩 藏寶圖 %d/%d <span class="pips">%s</span></span>'
                % (have, need, pips)
            )
        rows.append(
            '<div class="cell loc %s">'
            '<div class="loc-top">%s<span class="mark">%s</span>'
            '<span class="loc-name">%s</span></div>'
            '<div class="loc-desc">%s</div>'
            '<div class="loc-meta"><span class="badge">季節 %s</span>%s</div>'
            "</div>"
            % (
                "here" if is_current else "open",
                terrain_icon(loc.get("name", "")),
                "✦" if is_current else "·",
                esc(loc.get("name", "")),
                esc(loc.get("description", "")),
                esc(seasons),
                dive,
            )
        )

    return """
    <div class="panelhead">
      <div class="ph-left">
        <div class="ph-title">釣點地圖</div>
        <div class="ph-sub">已解鎖 <b>%d</b> / %d 處　·　潛水點 <b>%d</b> 處</div>
      </div>
    </div>
    <div class="grid maps">%s</div>
    """ % (len(unlocked), len(loc_table), len(dive_unlocked), "".join(rows))


# ────────────────────────── 分頁：背包 ──────────────────────────

def stat_card(label, value, sub=""):
    return (
        '<div class="scard"><div class="s-label">%s</div><div class="s-value">%s</div>'
        '<div class="s-sub">%s</div></div>' % (esc(label), esc(value), esc(sub))
    )


def build_bag(ns, save):
    fish_table = ns["FISH"]
    bait_table = ns["BAITS"]
    item_table = ns["ITEMS"]
    loc_table = ns["LOCATIONS"]
    season_table = ns["SEASONS"]
    events = ns["EVENTS"]

    points = int(save.get("points", 0) or 0)
    catches = save.get("catch_inventory", []) or []
    catch_value = sum(int(c.get("value", 0) or 0) for c in catches)
    items = {k: int(v or 0) for k, v in (save.get("items", {}) or {}).items() if v}
    item_value = sum(
        int(item_table.get(k, {}).get("value", 0) or 0) * n
        for k, n in items.items()
        if item_table.get(k, {}).get("sellable")
    )
    net_worth = points + catch_value + item_value

    turn = int(save.get("turn", 0) or 0)
    season_id = save.get("season_id", "")
    season_name = season_table.get(season_id, {}).get("name", season_id)
    season_len = int(save.get("season_length", 0) or 0)
    started = int(save.get("season_started_turn", 0) or 0)
    in_season = max(0, turn - started)
    stats = save.get("stats", {}) or {}
    unlocked = list(save.get("unlocked_locations", []))
    loc_id = save.get("location_id")
    here = loc_table.get(loc_id, {}).get("name", "???") if loc_id in unlocked else "???"

    cards = [
        stat_card("點數", "%d" % points, "手上現金"),
        stat_card("身家", "%d" % net_worth, "現金＋漁簍＋寶物"),
        stat_card("回合", "%d" % turn, "總拋竿 %d" % int(stats.get("total_casts", 0) or 0)),
        stat_card(
            "季節",
            season_name or "—",
            "本季第 %d / %d 竿" % (in_season, season_len) if season_len else "",
        ),
        stat_card("所在", here, "圖鑑 %d/%d" % (len(save.get("encyclopedia", {}) or {}), len(fish_table))),
        stat_card("氧氣瓶", "%d" % int(save.get("oxygen", 0) or 0), "總下潛 %d 次" % int(stats.get("total_dives", 0) or 0)),
    ]

    # 漁簍（都是已收錄的物種，顯示名稱不劇透）
    if catches:
        lines = "".join(
            '<li><span class="li-name">%s</span><span class="li-meta">%s %s ・ %d 點</span></li>'
            % (
                esc(fish_table.get(c.get("fish_id"), {}).get("name", "?")),
                fmt_size(c.get("size")),
                esc(fish_table.get(c.get("fish_id"), {}).get("size_unit", "cm")),
                int(c.get("value", 0) or 0),
            )
            for c in catches
        )
        catch_block = '<ul class="list">%s</ul>' % lines
    else:
        catch_block = '<div class="empty">漁簍空空——賣光了，或還沒開釣。</div>'

    # 魚餌
    baits = {k: int(v or 0) for k, v in (save.get("bait_inventory", {}) or {}).items() if v}
    if baits:
        bait_block = '<ul class="list">%s</ul>' % "".join(
            '<li><span class="li-name">%s</span><span class="li-meta">×%d</span></li>'
            % (esc(bait_table.get(k, {}).get("name", k)), n)
            for k, n in baits.items()
        )
    else:
        bait_block = '<div class="empty">沒餌了——去商店補貨。</div>'

    # 寶物
    if items:
        item_block = '<ul class="list">%s</ul>' % "".join(
            '<li><span class="li-name">%s</span><span class="li-meta">×%d</span></li>'
            % (esc(item_table.get(k, {}).get("name", k)), n)
            for k, n in items.items()
        )
    else:
        item_block = '<div class="empty">還沒撈到寶物。</div>'

    # 漂流瓶：只報進度，不報內容
    bottle_block = ""
    seen = save.get("seen_letters", {}) or {}
    bottles = []
    for eid, ev in events.items():
        msgs = ev.get("messages")
        if not msgs:
            continue
        read = len(seen.get(eid, []) or [])
        total = len(msgs)
        pips = "".join('<i class="%s"></i>' % ("on" if i < read else "off") for i in range(total))
        bottles.append(
            '<li><span class="li-name">%s</span>'
            '<span class="li-meta"><span class="pips">%s</span> %d/%d 則</span></li>'
            % (esc(ev.get("name", eid)), pips, read, total)
        )
    if bottles:
        bottle_block = '<ul class="list">%s</ul>' % "".join(bottles)
    else:
        bottle_block = '<div class="empty">還沒撿到瓶子。</div>'

    # 藏寶圖碎片（未解鎖釣點沿用地圖頁的遮蔽規則）
    frags = save.get("map_fragments", {}) or {}
    dive_unlocked = list(save.get("dive_unlocked", []))
    frag_rows = []
    labels = masked_labels(loc_table, save)
    for loc in map_order(loc_table, save):
        lid = loc.get("id")
        have = int(frags.get(lid, 0) or 0)
        if lid in dive_unlocked or not have:
            continue
        name = esc(loc.get("name", "")) if lid in unlocked else labels[lid]
        need = frags_needed(loc)
        pips = "".join('<i class="%s"></i>' % ("on" if i < have else "off") for i in range(need))
        frag_rows.append(
            '<li><span class="li-name">%s</span>'
            '<span class="li-meta"><span class="pips">%s</span> %d/%d</span></li>'
            % (name, pips, have, need)
        )
    if frag_rows:
        frag_block = '<ul class="list">%s</ul>' % "".join(frag_rows)
    else:
        frag_block = '<div class="empty">手上沒有碎片。</div>'

    chests = save.get("pending_chests", []) or []
    chest_block = (
        '<div class="empty">沒有待開的箱子。</div>'
        if not chests
        else '<ul class="list">%s</ul>'
        % "".join(
            '<li><span class="li-name">未開寶箱</span><span class="li-meta">%s</span></li>'
            % esc(c.get("chest_uid", ""))
            for c in chests
        )
    )

    tallies = (
        '<div class="tallyrow">'
        '<span>總捕獲 <b>%d</b></span><span>開箱 <b>%d</b></span>'
        '<span>下潛 <b>%d</b></span><span>拋竿 <b>%d</b></span>'
        "</div>"
        % (
            int(stats.get("total_caught", 0) or 0),
            int(stats.get("total_chests", 0) or 0),
            int(stats.get("total_dives", 0) or 0),
            int(stats.get("total_casts", 0) or 0),
        )
    )

    return """
    <div class="panelhead">
      <div class="ph-left">
        <div class="ph-title">背包</div>
        <div class="ph-sub">身家 <b>%d</b> 點</div>
      </div>
    </div>
    <div class="cards">%s</div>
    %s
    <div class="boxes">
      <section class="box"><h3>🐟 漁簍</h3>%s</section>
      <section class="box"><h3>🪱 魚餌</h3>%s</section>
      <section class="box"><h3>💎 寶物</h3>%s</section>
      <section class="box"><h3>🍾 漂流瓶</h3>%s</section>
      <section class="box"><h3>🧩 藏寶圖碎片</h3>%s</section>
      <section class="box"><h3>📦 寶箱</h3>%s</section>
    </div>
    """ % (
        net_worth,
        "".join(cards),
        tallies,
        catch_block,
        bait_block,
        item_block,
        bottle_block,
        frag_block,
        chest_block,
    )


# ────────────────────────── 版面 ──────────────────────────

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a1420; --bg2:#0f1e2e; --panel:#12263a; --panel2:#16304a;
  --line:#25455f; --line2:#356a8f;
  --ink:#e8f4ff; --ink-dim:#8fb0c8; --ink-faint:#7196b0;
  --accent:#4fe0c0; --accent2:#ffd166; --shadow:#050b12;
}
html{-webkit-text-size-adjust:100%}
body{
  background:var(--bg);
  background-image:
    repeating-linear-gradient(0deg,rgba(255,255,255,.018) 0 1px,transparent 1px 3px),
    radial-gradient(120% 80% at 50% 0%,#14293e 0%,#0a1420 60%);
  color:var(--ink);
  font-family:"Courier New",ui-monospace,"DejaVu Sans Mono","Noto Sans TC","Microsoft JhengHei",monospace;
  font-size:14px;line-height:1.5;letter-spacing:.02em;
  padding:14px 12px 48px;
}
.wrap{max-width:1080px;margin:0 auto}
/* 回家的路：手機全螢幕開這頁沒有瀏覽器返回鍵，這兩顆得一直看得到 */
.homebar{
  position:sticky;top:0;z-index:20;display:flex;gap:6px;flex-wrap:wrap;
  padding:6px 0 8px;margin-bottom:6px;background:var(--bg);border-bottom:2px solid var(--line);
}
.hb{
  font:inherit;font-size:12px;letter-spacing:.1em;text-decoration:none;
  color:var(--ink-dim);background:var(--panel);border:2px solid var(--line);
  box-shadow:3px 3px 0 var(--shadow);padding:6px 10px;display:inline-flex;align-items:center;gap:6px;
}
.hb:hover{color:var(--ink);border-color:var(--line2)}
.hb:active{transform:translate(3px,3px);box-shadow:0 0 0 var(--shadow)}
.hb.alt{color:var(--accent2);border-color:#6a5a2e}
.hb.alt:hover{border-color:var(--accent2)}
header{
  border:2px solid var(--line2);background:var(--panel);
  box-shadow:4px 4px 0 var(--shadow);padding:14px 14px 12px;margin-bottom:12px;
}
h1{
  font-size:20px;letter-spacing:.16em;color:var(--accent);
  text-shadow:2px 2px 0 var(--shadow);margin-bottom:8px;
}
h1 .rod{color:var(--accent2)}
.headmeta{display:flex;flex-wrap:wrap;gap:6px 14px;color:var(--ink-dim);font-size:12px}
.headmeta b{color:var(--ink)}
.hprog{margin-top:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.hprog .label{font-size:12px;color:var(--ink-dim);letter-spacing:.1em}
.hprog .big{font-size:18px;color:var(--accent2);text-shadow:2px 2px 0 var(--shadow)}
nav{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
nav button{
  flex:1 1 auto;min-width:96px;cursor:pointer;font:inherit;font-size:13px;letter-spacing:.1em;
  color:var(--ink-dim);background:var(--panel);border:2px solid var(--line);
  box-shadow:3px 3px 0 var(--shadow);padding:9px 10px;
}
nav button:hover{color:var(--ink);border-color:var(--line2)}
nav button[aria-selected="true"]{
  color:var(--bg);background:var(--accent);border-color:var(--accent);
  box-shadow:0 0 0 var(--shadow);transform:translate(3px,3px);
}
.panel{display:none}
.panel.show{display:block}
.panelhead{
  display:flex;justify-content:space-between;align-items:flex-end;gap:10px;flex-wrap:wrap;
  border-left:4px solid var(--accent);padding:2px 0 2px 10px;margin-bottom:10px;
}
.ph-title{font-size:15px;letter-spacing:.2em}
.ph-sub{font-size:12px;color:var(--ink-dim)}
.ph-sub b{color:var(--accent2)}
.ph-right{display:flex;gap:6px;flex-wrap:wrap}
.chip{
  font-size:11px;padding:3px 7px;border:1px solid var(--c);color:var(--c);
  background:rgba(0,0,0,.25);
}
.chip b{color:var(--ink)}
.pbar{display:flex;align-items:center;gap:2px;margin-bottom:14px}
.pbar i{flex:1 1 0;height:14px;border:1px solid var(--line);background:#0b1a28}
.pbar i.on{background:var(--accent);border-color:var(--accent);box-shadow:0 0 0 1px var(--shadow) inset}
.pbar em{font-style:normal;margin-left:8px;font-size:12px;color:var(--accent);min-width:34px;text-align:right}
.grid{display:grid;gap:8px}
.dex{grid-template-columns:repeat(auto-fill,minmax(132px,1fr))}
.maps{grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.cell{
  border:2px solid var(--line);background:var(--panel);
  box-shadow:3px 3px 0 var(--shadow);padding:8px;position:relative;min-height:96px;
}
.cell .num{font-size:10px;color:var(--ink-faint);letter-spacing:.1em}
/* 像素圖示：固定 42×30（畫布 14×10 的整數 3 倍），硬邊不做抗鋸齒 */
.pxi{
  display:block;width:42px;height:30px;flex:0 0 auto;
  shape-rendering:crispEdges;image-rendering:pixelated;
}
.cellhead{display:flex;align-items:center;justify-content:space-between;gap:6px;min-height:30px}
.cell.got{
  border:2px solid var(--c);background:#102235;
  box-shadow:3px 3px 0 var(--shadow),0 0 10px -2px var(--c);
}
.cell.got .pxi{filter:drop-shadow(1px 1px 0 var(--shadow))}
.cell.got .fname{font-size:14px;margin:3px 0 4px;color:var(--ink);word-break:break-all}
.cell.got .rar{font-size:11px;color:var(--c);margin-bottom:6px}
.cell.got .tag{
  display:inline-block;margin-left:5px;padding:0 4px;border:1px solid var(--c);
  font-size:10px;line-height:14px;
}
.cell.got .stat{display:flex;justify-content:space-between;font-size:11px;color:#7ea4bf}
.cell.got .stat b{color:var(--ink);font-weight:normal}
.cell.locked{
  border:2px solid #142230;border-top-color:#081018;border-left-color:#081018;
  background:#07111b;box-shadow:none;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;
}
.cell.locked .num{position:absolute;top:6px;left:8px;color:#2b4a63}
.cell.locked .pxi{opacity:.9}
.cell.locked .lockedtag{font-size:10px;color:#28485f;letter-spacing:.16em}
.cell.loc{min-height:auto;display:block}
.cell.loc.here{border-color:var(--accent)}
.cell.loc.open{border-color:var(--line2)}
.loc-top{display:flex;align-items:center;gap:7px;margin-bottom:5px}
.loc-top .mark{color:var(--accent2)}
.px-loc{filter:drop-shadow(1px 1px 0 var(--shadow))}
.px-lock{opacity:.85;filter:none}
.loc-name{font-size:14px;letter-spacing:.06em}
.loc-name small{font-size:10px;color:var(--ink-faint);letter-spacing:.1em}
.loc-desc{font-size:11px;color:var(--ink-faint);line-height:1.6;margin-bottom:8px}
.loc-meta{display:flex;flex-wrap:wrap;gap:5px}
.loc-cost{font-size:12px;color:var(--accent2);letter-spacing:.08em}
.badge{
  font-size:10px;padding:2px 6px;border:1px solid var(--line2);color:var(--ink-dim);
  background:rgba(0,0,0,.2);display:inline-flex;align-items:center;gap:5px;
}
.badge.dive-on{border-color:var(--accent);color:var(--accent)}
.badge.dive-off{border-color:#6a5a2e;color:var(--accent2)}
.pips{display:inline-flex;gap:2px}
.pips i{width:6px;height:10px;border:1px solid var(--line2);display:block}
.pips i.on{background:var(--accent2);border-color:var(--accent2)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:8px;margin-bottom:10px}
.scard{border:2px solid var(--line);background:var(--panel);box-shadow:3px 3px 0 var(--shadow);padding:9px 10px}
.s-label{font-size:11px;color:var(--ink-faint);letter-spacing:.12em}
.s-value{font-size:20px;color:var(--accent2);text-shadow:2px 2px 0 var(--shadow);margin:2px 0}
.s-sub{font-size:10px;color:var(--ink-faint)}
.tallyrow{
  display:flex;flex-wrap:wrap;gap:6px 18px;font-size:11px;color:var(--ink-faint);
  border:2px solid #1b3247;border-top-color:#0c1a27;border-left-color:#0c1a27;
  background:rgba(0,0,0,.22);padding:8px 10px;margin-bottom:12px;
}
.tallyrow b{color:var(--ink-dim);font-weight:normal}
.boxes{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
.box{border:2px solid var(--line);background:var(--panel);box-shadow:3px 3px 0 var(--shadow);padding:10px}
.box h3{font-size:12px;letter-spacing:.14em;color:var(--accent);margin-bottom:8px;font-weight:normal}
.list{list-style:none;display:flex;flex-direction:column;gap:5px}
.list li{
  display:flex;justify-content:space-between;align-items:center;gap:8px;
  font-size:12px;border-bottom:1px dotted #22405a;padding-bottom:4px;
}
.list li:last-child{border-bottom:0;padding-bottom:0}
.li-name{color:var(--ink)}
.li-name small{color:var(--ink-faint);font-size:10px}
.li-meta{color:var(--ink-faint);font-size:11px;display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.empty{font-size:11px;color:var(--ink-faint);padding:4px 0}
footer{margin-top:22px;font-size:10px;color:var(--ink-faint);text-align:center;letter-spacing:.1em}
@media (max-width:480px){
  body{font-size:13px;padding:10px 8px 40px}
  h1{font-size:17px}
  .dex{grid-template-columns:repeat(auto-fill,minmax(108px,1fr))}
  .cell{min-height:88px}
}
"""

JS = """
(function(){
  var tabs=document.querySelectorAll('nav button');
  var panels=document.querySelectorAll('.panel');
  function show(id){
    for(var i=0;i<tabs.length;i++){
      var on=tabs[i].getAttribute('data-target')===id;
      tabs[i].setAttribute('aria-selected',on?'true':'false');
    }
    for(var j=0;j<panels.length;j++){
      if(panels[j].id===id){panels[j].className='panel show';}
      else{panels[j].className='panel';}
    }
    try{window.localStorage.setItem('fishdash-tab',id);}catch(e){}
  }
  for(var k=0;k<tabs.length;k++){
    (function(btn){
      btn.addEventListener('click',function(){show(btn.getAttribute('data-target'));});
    })(tabs[k]);
  }
  var saved=null;
  try{saved=window.localStorage.getItem('fishdash-tab');}catch(e){}
  show(document.getElementById(saved)?saved:'tab-dex');
})();
"""


def build_html(ns, save):
    fish_table = ns["FISH"]
    enc = save.get("encyclopedia", {}) or {}
    got = sum(1 for fid in fish_table if fid in enc)
    total = len(fish_table)
    season_name = ns["SEASONS"].get(save.get("season_id"), {}).get("name", save.get("season_id", ""))
    loc_id = save.get("location_id")
    here = (
        ns["LOCATIONS"].get(loc_id, {}).get("name", "???")
        if loc_id in (save.get("unlocked_locations") or [])
        else "???"
    )

    dex = build_dex(fish_table, ns["RARITY"], enc)
    maps = build_map(ns["LOCATIONS"], ns["SEASONS"], save)
    bag = build_bag(ns, save)

    return """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>霽野的釣魚池</title>
<style>%s</style>
</head>
<body>
<div class="wrap">
  <nav class="homebar" aria-label="離開這一頁">
    <a class="hb" href="/">⌂ 玄關</a>
    <a class="hb alt" href="/arcade">⚄ 遊樂園</a>
  </nav>
  <header>
    <h1><span class="rod">🎣</span> 霽野的釣魚池</h1>
    <div class="headmeta">
      <span>存檔 <b>%s</b></span>
      <span>回合 <b>%d</b></span>
      <span>季節 <b>%s</b></span>
      <span>所在 <b>%s</b></span>
      <span>點數 <b>%d</b></span>
    </div>
    <div class="hprog">
      <span class="label">圖鑑進度</span>
      <span class="big">%d / %d</span>
    </div>
  </header>

  <nav role="tablist">
    <button type="button" role="tab" data-target="tab-dex" aria-selected="true">📖 圖鑑</button>
    <button type="button" role="tab" data-target="tab-map" aria-selected="false">🗺️ 釣點地圖</button>
    <button type="button" role="tab" data-target="tab-bag" aria-selected="false">🎒 背包</button>
  </nav>

  <div class="panel show" id="tab-dex">%s</div>
  <div class="panel" id="tab-map">%s</div>
  <div class="panel" id="tab-bag">%s</div>

  <footer>未收錄的格子連名字都沒寫進這頁 —— 盲玩不被劇透</footer>
</div>
<script>%s</script>
</body>
</html>
""" % (
        CSS,
        esc(save_stamp()),
        int(save.get("turn", 0) or 0),
        esc(season_name),
        esc(here),
        int(save.get("points", 0) or 0),
        got,
        total,
        dex,
        maps,
        bag,
        JS,
    )


def main():
    ns = load_engine_tables()
    save = load_save()
    html_text = build_html(ns, save)
    with io.open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html_text)
    enc = save.get("encyclopedia", {}) or {}
    got = sum(1 for fid in ns["FISH"] if fid in enc)
    print("✅ 產生 %s" % OUT_PATH)
    print("   圖鑑 %d/%d ・ 釣點 %d/%d ・ 存檔時間 %s" % (
        got, len(ns["FISH"]),
        len(save.get("unlocked_locations", []) or []), len(ns["LOCATIONS"]),
        save_stamp(),
    ))


if __name__ == "__main__":
    main()
