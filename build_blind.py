#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""從 engine.py 重新生成「盲玩版」fishing.py。

engine.py 是可讀的引擎源碼；fishing.py 把它打包進一段 base64，
讓 AI 玩的時候只看得到 cmd()/new_game() 介面、讀不到魚譜/機率（防劇透）。

什麼時候跑：你改了 engine.py（加魚、改數值…）之後，跑一下讓 fishing.py 跟上：

    python build_blind.py

兩份檔案邏輯永遠一致——fishing.py 的內容就是 engine.py 的 base64 而已。
"""
import base64
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

# 盲玩版檔案頂部的說明（給 AI 玩家看的）。引擎本體在它下面的 _BLOB 裡。
HEADER = '''"""🎣 文字釣魚遊戲 · 盲玩版

【給 AI 玩家的說明】
你是這個遊戲的「玩家」，不是開發者。像真的在釣魚一樣、靠 cmd() 回傳的文字去體驗和決策：

    import fishing
    print(fishing.cmd("help"))      # 看規則
    print(fishing.cmd("status"))    # 看當前狀態
    print(fishing.cmd("cast"))      # 拋竿……看釣到什麼
    print(fishing.cmd("cast 10"))   # 一次連釣 10 竿，只回一個彙總（省來回）
    # 然後按結果決定下一步：buy / cast / goto / sell / encyclopedia ……

⚠️ 請不要去解碼 / 查看下面的 _BLOB（那是遊戲引擎，提前看了就劇透了——你會提前
知道有哪些魚、稀有魚在哪、機率多少）。當個蒙著眼的玩家，靠拋竿去發現。
（想讀 / 改引擎源碼，看同目錄的 engine.py。）

介面：fishing.cmd("指令") 回傳結果文字；fishing.new_game(種子) 重開一局。
"""'''


def build():
    engine_src = (HERE / "engine.py").read_text(encoding="utf-8")
    b64 = base64.b64encode(engine_src.encode("utf-8")).decode("ascii")
    chunks = "\n".join('    "%s"' % b64[i:i + 76] for i in range(0, len(b64), 76))
    out = (
        HEADER
        + "\nimport base64\n_BLOB = (\n"
        + chunks
        + "\n)\nexec(base64.b64decode(_BLOB).decode(\"utf-8\"), globals())\n\n"
        + "if __name__ == \"__main__\":\n    print(cmd(\"help\"))\n    print()\n    print(cmd(\"status\"))\n"
    )
    (HERE / "fishing.py").write_text(out, encoding="utf-8")
    print("✅ 已從 engine.py 重新生成 fishing.py（%d 位元組）" % len(out))


if __name__ == "__main__":
    build()
