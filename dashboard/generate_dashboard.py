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

    cells = []
    for idx, fid in enumerate(order, start=1):
        num = "%02d" % idx
        rec = enc.get(fid)
        if not rec:
            # 未收錄：只有編號與剪影，不寫入任何來自引擎的欄位
            cells.append(
                '<div class="cell locked"><div class="num">#%s</div>'
                '<div class="silhouette">?<span>?</span>?</div>'
                '<div class="lockedtag">未收錄</div></div>' % num
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
            '<div class="num">#%s</div>'
            '<div class="fname">%s</div>'
            '<div class="rar">%s<span class="tag">%s</span></div>'
            '<div class="stat"><span>最大</span><b>%s %s</b></div>'
            '<div class="stat"><span>捕獲</span><b>%d 次</b></div>'
            '<div class="stat"><span>初遇</span><b>第 %s 回合</b></div>'
            "</div>"
            % (
                color,
                num,
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

    rows = []
    for loc in map_order(loc_table, save):
        lid = loc.get("id")
        is_unlocked = lid in unlocked
        is_current = lid == current
        if not is_unlocked:
            # 未解鎖：名稱遮蔽，只留解鎖點數（商店本來就看得到）
            rows.append(
                '<div class="cell loc locked">'
                '<div class="loc-top"><span class="mark">🔒</span>'
                '<span class="loc-name">%s</span></div>'
                '<div class="loc-cost">%d 點解鎖</div>'
                "</div>" % (labels[lid], int(loc.get("unlock_cost", 0) or 0))
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
            '<div class="loc-top"><span class="mark">%s</span>'
            '<span class="loc-name">%s</span></div>'
            '<div class="loc-desc">%s</div>'
            '<div class="loc-meta"><span class="badge">季節 %s</span>%s</div>'
            "</div>"
            % (
                "here" if is_current else "open",
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
.cell.got{
  border:2px solid var(--c);background:#102235;
  box-shadow:3px 3px 0 var(--shadow),0 0 10px -2px var(--c);
}
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
.cell.locked .silhouette{
  font-size:18px;letter-spacing:.18em;color:#183248;opacity:.6;text-shadow:2px 2px 0 #050c14;
}
.cell.locked .silhouette span{color:#1d3c55}
.cell.locked .lockedtag{font-size:10px;color:#28485f;letter-spacing:.16em}
.cell.loc{min-height:auto;display:block}
.cell.loc.here{border-color:var(--accent)}
.cell.loc.open{border-color:var(--line2)}
.loc-top{display:flex;align-items:baseline;gap:7px;margin-bottom:5px}
.loc-top .mark{color:var(--accent2)}
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
