# 🎣 文字釣魚 · 給 AI 玩的確定性小遊戲

一個**單檔案、零依賴、確定性**的文字釣魚遊戲 —— 專門做來**讓你的 AI 伴侶來玩**的。

買餌 → 拋竿 → 按稀有度釣上各種魚 → 賣魚換點數 → 解鎖新水域 → 集齊圖鑑。
55 種魚、11 個釣點、四季流轉、漂流瓶/寶箱/寶物、稀有度儀式感文案……一竿一竿釣下去，看你的 AI 怎麼經營、怎麼為一條傳說魚上鉤而激動。

> **它只給玩法邏輯（引擎）。怎麼接到你自己的 AI 上，由你配置** —— 下面「接到你的 AI 上」一節給了三種接法草圖。

> ### 📦 兩個版本，分開下載（見 [Releases](https://github.com/tutusagi/ai-fishing-game/releases)）
> - **v2.0 · 潛水完整版**（`main`，本文件）：在精簡版基礎上加了整套潛水玩法——藏寶圖碎片解鎖潛水點、22 種水下專屬魚（帶捕獲手感）、按地點×季節的下潛氛圍、14 種水下奇遇、21 件寶物、海底寶庫、氧氣瓶套餐。
> - **v1.2 · 精簡版**（`v1.2-lite` 分支）：只含操作/省 token 最佳化（batch 疊加指令 / 狀態欄 JSON / 釣點待發現計數 / 連釣提示）+ 6 個幸運事件，**不含潛水**，更輕量。

---

## 這是什麼 / 為什麼是「給 AI 玩」

普通文字遊戲是給人玩的。這個引擎從設計上就是給 **AI 玩家**用的：

- **確定性**：內建 mulberry32 PRNG，狀態全部序列化進存檔。**同一個種子 + 同一串指令 = 逐位可復現的結果**。便於回顧、測試、分享同一局。
- **盲玩**：可以讓 AI 在**不劇透**的前提下玩 —— 它不知道有哪些魚、稀有魚在哪、機率多少，全靠一竿一竿親手發現。
- **存檔獨立**：遊戲狀態存在磁碟檔案裡，**不在對話上下文裡**。AI 的對話被清空，釣魚進度也不會丟。
- **省 token**：支援一次「連釣 N 竿」，只回一個彙總（精彩的留全文、雜魚摺疊成清點）；還能用 `;` 或換行把多條指令串成一批一次跑（買餌→拋竿、換地點→拋竿）。每次回覆末尾附一行緊湊 `📊` 狀態欄 JSON，AI 看它就夠、不必反覆查狀態。不用一竿一條訊息來回燒上下文。

---

## 儲存庫裡有什麼

| 檔案 | 是什麼 | 你怎麼用 |
|---|---|---|
| **`engine.py`** | **可讀的引擎源碼**。對外只用兩個介面：`cmd("指令")` 回傳結果文字、`new_game(seed)` 重開一局。 | 想讀懂 / 改數值 / 加魚加地點，就看這個。也可以直接 `import engine` 當庫用。 |
| **`fishing.py`** | **盲玩版**。引擎被打包進檔案裡、藏起來，只露 `cmd()`/`new_game()`。 | 想讓 AI **不劇透**地玩，就把這個檔案給它（它讀不到魚譜/機率，只能靠拋竿發現）。 |
| `build_blind.py` | 從 `engine.py` 重新生成 `fishing.py` 的小腳本。 | 改了 `engine.py` 後跑 `python build_blind.py`，讓盲玩版跟上。 |
| `tool-schema.json` | `play_fishing` 工具的 JSON Schema（函式呼叫接法用）。 | 用「函式呼叫 / tool use」接 AI 時的參考。 |
| `examples/` | 接法示例。 | 照著接。 |

> `engine.py` 和 `fishing.py` 是**同一個遊戲**，只是 `fishing.py` 把引擎藏了起來防劇透。二選一即可，或都放著。

---

## 快速開始（自己先玩兩把）

需要 Python 3.8+。

```python
import engine            # 或 import fishing（盲玩版，介面一樣）

print(engine.cmd("help"))            # 看規則
print(engine.cmd("status"))          # 看當前狀態
print(engine.cmd("cast"))            # 拋一竿
print(engine.cmd("cast 10"))         # 一次連釣 10 竿（只回一個彙總）
print(engine.cmd("cast 20 stop=rare"))  # 連釣 20 竿，釣到稀有就停
print(engine.cmd("buy basic_worm 10; cast 10"))  # 多條指令串一批、一次跑完
print(engine.new_game(2024))         # 用種子 2024 重開一局
```

> **Windows 使用者**：遊戲裡有中文和 emoji。如果終端顯示出現亂碼或 `UnicodeEncodeError`，讓主控台走 UTF-8 即可，三選一：
> - 設環境變數 `PYTHONUTF8=1` 再執行（推薦）；
> - 或在終端先執行 `chcp 65001`；
> - 或在程式碼開頭加 `import sys; sys.stdout.reconfigure(encoding="utf-8")`。
> （檔案本身是 UTF-8、引擎沒問題，這只是終端顯示的事。）

> 任何輸入都安全：`cmd("...")` 對亂七八糟的指令也只會**回傳一句提示文字**，不會拋例外炸堆疊；存檔讀/寫出問題（損壞 / 目錄不可寫）也會在回傳裡**明確告訴你**，不會假裝存好了。

---

## 玩法

- **買餌 → 拋竿（cast）**：拋竿是核心。按稀有度機率釣上常見 / 少見 / 稀有 / 史詩 / 傳說 / 神話各檔的魚。
- **每個地點 + 季節出的魚不同**：想集齊圖鑑，得 `goto` 換地點、留意季節（季節隨拋竿數推進）。
- **賣魚 / 賣寶（sell）換點數**，點數用來買好餌、**解鎖新水域**。
- **拋竿偶遇**漂流瓶（收集紙條）、寶箱（要鑰匙或花點數開）、寶物。
- **幸運時刻**：釣到魚時小機率觸發——分裂魚鉤（一竿上三條）、點石成金（這條價值×3）、漁獲熱潮（接下來幾條翻倍）、河神的祝福（幾竿不耗餌）、千載難逢的漲潮（破紀錄大魚）、蚌中生珠（掏出財寶）。
- **潛水遠征（dive）**：潛水是後期玩法——**解鎖第一個潛水點後，商店才上架氧氣瓶**。買氧氣瓶（買 5 瓶 8 折、10 瓶 7 折）後 `dive` 開一趟「遠征」：帶 N 瓶氧氣當深度預算，捕獲只有水下才有的魚種（水面釣不到），上岸出一份**遠征結算**（漁獲/寶物/新發現/氧氣花費/淨值）。途中遇到**「大遺蹟」會暫停**讓你 `choose` 抉擇——每個選項**消耗不同氧氣**（氧氣不夠就只能放棄），通往不同的魚種/寶物/故事。`surface` 可隨時上浮。每次下潛頂部還有一句當地當季的「下潛實況」（水溫/見聞/要不要防護服）。
- **解鎖潛水點（藏寶圖碎片）**：每個釣點的潛水要先解鎖——在該地**水面釣魚**會隨機撈到「藏寶圖碎片」，集齊 3~5 塊（按水域深淺）自動拼成藏寶圖，解鎖這裡的潛水。碎片也能從**漂流瓶、寶箱**裡開出；運氣好還能開出**稀有的完整藏寶圖**，直接解鎖一處潛水點。
- **水下奇遇**：潛水時小機率撞見 14 種水下奇觀（珊瑚宮 / 人魚宮殿 / 沉船墓場 / 鯨落 / 海妖巢穴 / 龍王宮闕 / 失落的鐘樓…），撿到珍寶、古遺物、氧氣或寶箱（水面不會遇到）。
- **集圖鑑**：第一次釣到某種魚會記入圖鑑（賣掉也不丟記錄），首次發現還有額外點數獎勵。

開局：200 點 + 普通蚯蚓×5，在「月光池塘」（和「蘆葦河」已解鎖）。

## 指令清單（傳給 `cmd("...")`）

| 指令 | 作用 |
|---|---|
| `help` | 看規則 |
| `status` | 點數 / 地點 / 季節 / 魚餌 / 圖鑑進度 |
| `shop` | 看可買魚餌 |
| `buy <餌id> [數量]` | 買餌，如 `buy glow_bait 2`；買氧氣瓶 `buy oxygen 5` |
| `cast [餌id] [次數] [stop=new,rare,event]` | 拋竿。不填餌=用最便宜的；帶次數=連釣 N 竿（1~20）；`stop=` 遇新種(new)/稀有(rare)/事件(event=漂流瓶·寶箱·寶物·水下奇遇)就提前停，可逗號多選 |
| `dive [帶幾瓶] [stop=...]` | 開潛水遠征（先 `buy oxygen`）。帶 N 瓶氧氣下水捕水下魚；遇大遺蹟暫停 |
| `choose <編號>` | 在大遺蹟處抉擇（每個選項耗不同氧氣；不帶編號=重看選項） |
| `surface` | 主動結束遠征、上浮上岸 |
| `goto` | **不帶參數 = 列出所有釣點**（價格 / 本季還有幾種沒見過的魚，含單列的傳說級） |
| `goto <地點id>` | 前往該地點（未解鎖則花點數解鎖） |
| `inventory` | 漁簍 + 物品 + 待開寶箱 |
| `sell <實例id> \| sell all \| sell species <魚id> \| sell item <物品id>` | 賣魚 / 賣財寶換點數 |
| `open <寶箱uid>` | 打開釣上來的寶箱 |
| `encyclopedia` | 圖鑑收集進度 |
| `look <id或中文名>` | 細看魚 / 地點 / 魚餌 / 季節 / 物品（沒釣到的魚顯示 ？？？） |
| `A; B; C`（`;` 或換行串聯） | 把多條指令排成一批、一次按序執行（最多 8 條），如 `buy basic_worm 10; cast 10`、`goto reed_river; cast 8 stop=new` |

### 連釣省 token（重點）

AI 一竿一條訊息會反覆來回燒上下文。用 `cast <次數>` 一次連釣：

```
cast 10                # 連釣 10 竿
cast glow_bait 15 stop=rare   # 用夜光餌連釣 15 竿，釣到稀有及以上就停
```

回傳是**一個彙總**：新種 / 稀有 / 事件 / 換季這些**精彩時刻留完整文案**，重複的雜魚和空軍**摺疊成一行清點**。一次連釣把「≈2N 次往返」壓成「≈2 次」。

### 疊加指令一次跑（batch）

用 `;` 或換行把多條不同指令串成一批、一次按順序執行（最多 8 條），常見的「買餌→拋竿」「換地點→拋竿」一次搞定：

```
buy basic_worm 10; cast 10            # 先買 10 個蚯蚓，再連釣 10 竿
goto reed_river; cast 8 stop=new      # 換到蘆葦河，連釣 8 竿、釣到新種就停
```

每段前面帶 `▶ 指令` 小標題，按序輸出。某條出錯只影響那一條、不打斷後面的。

### 狀態欄 JSON（每次都附）

每次 `cmd()` 回傳的**末尾都有一行**緊湊機讀狀態欄，AI 看它就夠、不必再單獨 `status`：

```
📊 {"pts": 270, "loc": "蘆葦河", "sea": "春", "turn": 6, "enc": "5/55", "bait": {"basic_worm": 2}, "hold": 6}
```

`pts` 點數 · `loc/sea` 當前地點/季節 · `turn` 回合 · `enc` 圖鑑進度 · `bait` 餘餌 · `hold` 未賣漁獲條數（有待開寶箱時多一個 `chest`）。

## 存檔 & 確定性

- 狀態存在**和腳本同目錄**的 `fishing_save.json`。刪掉它 = 從頭開始。
- 確定性：mulberry32 PRNG，隨機狀態序列化進存檔。**同 seed + 同指令序列 → 結果完全一致**。預設種子 `0x9e3779b9`。
- 想多人各自一局：給每個玩家一個獨立的工作目錄（各有各的 `fishing_save.json`）。

---

## 接到你的 AI 上（三種接法，自己挑）

引擎只負責玩法邏輯，**怎麼讓你的 AI 呼叫它，由你按自己的棧配置**。三種常見姿勢：

### ① AI 有程式碼執行（最簡單）
ChatGPT 程式碼解釋器 / Claude 帶程式碼執行 / 自帶沙箱的 agent：
把 `fishing.py`（盲玩版）丟給它，讓它：

```python
import fishing
print(fishing.cmd("status"))
# 然後根據回傳文字決定下一步，反覆呼叫 cmd("cast")/cmd("buy ...")/cmd("goto ...")
```

見 `examples/play_with_code_interpreter.md`。

### ② 函式呼叫 / Tool use
把 `tool-schema.json` 裡的 `play_fishing` 註冊成一個工具。你的工具處理函式收到結構化參數後，轉成指令字串調 `engine.cmd()`，再把回傳文字餵回模型：

```python
import engine

def play_fishing(args: dict) -> str:
    a = args["action"]
    if a in ("cast", "dive"):
        parts = [a]
        if a == "cast" and args.get("bait_id"): parts.append(args["bait_id"])
        if args.get("times"):   parts.append(str(args["times"]))
        if args.get("stop_on"): parts.append("stop=" + ",".join(args["stop_on"]))
        return engine.cmd(" ".join(parts))
    if a == "choose":  return engine.cmd(f"choose {args.get('choice','')}".strip())   # 大遺蹟抉擇
    if a == "surface": return engine.cmd("surface")
    if a == "buy":   return engine.cmd(f"buy {args.get('bait_id','')} {args.get('qty',1)}")  # bait_id=\"oxygen\" 即買氧氣瓶
    if a == "goto":  return engine.cmd(f"goto {args.get('location_id','')}".strip())
    if a == "sell":  return engine.cmd(f"sell {args.get('target','')}")
    if a == "open":  return engine.cmd(f"open {args.get('chest_uid','')}")
    if a == "look":  return engine.cmd(f"look {args.get('id','')}")
    return engine.cmd(a)   # status / shop / inventory / encyclopedia
```

**更省事的替代**：不想用結構化參數，就註冊一個只有一個字串參數 `command` 的工具，處理函式直接 `return engine.cmd(command)`。模型自己寫 `"cast 10 stop=rare"` 這種指令——這種字串接法**天然支援疊加指令**，模型直接寫 `"buy basic_worm 10; cast 10"` 就一次跑完。（結構化接法要支援 `batch`，就把 `steps` 裡每步轉成指令串、用 `"; "` 連起來傳給一次 `engine.cmd()`。）

### ③ 自己寫迴圈
最樸素：模型輸出一條指令 → 你 `engine.cmd(指令)` → 把回傳文字塞回對話 → 模型決定下一步 → 循環。

---

## 盲玩說明（防劇透）

想讓 AI 像真玩家一樣**靠拋竿發現**、而不是提前知道有哪些魚 / 機率：

- 給它 **`fishing.py`**（引擎藏在打包資料裡），別給 `engine.py`。
- 告訴它：只調 `cmd()`，別去解碼 / 讀檔案裡那段打包資料。

> 坦白說：打包只是編碼、不是加密，鐵了心要偷看的模型一行程式碼就能解開。盲玩本質靠**配合**。正經玩的模型照著說明來就不會劇透。

---

## 內容規模

55 種水面魚（跨常見 / 少見 / 稀有 / 史詩 / 傳說 / 神話 6 檔）+ 22 種潛水專屬水下魚（帶捕獲手感）+ 潛水氛圍句（按地點×季節）+ 14 種水下奇遇（含 5 個帶抉擇的「大遺蹟」）+ 25 件寶物 + 8 條遺蹟專屬魚 · 11 個釣點（2 個免費 + 9 個 200~800 點解鎖）· 4 季節（每 20 竿推進一季）· 3 種魚餌 + 氧氣瓶潛水 · 漂流瓶 / 寶箱 / 寶物事件 · 6 種幸運隨機事件 · 物品與點數經濟 · 圖鑑收集 · 稀有度儀式感播報 + 地點氛圍/性格句。

## 改造 / 擴展

所有內容（魚 / 地點 / 魚餌 / 季節 / 事件 / 物品）都是 `engine.py` 頂部的純資料表，加內容只改資料、不動邏輯。

改完 `engine.py` 後，如果你用盲玩版，跑一下讓它跟上：

```bash
python build_blind.py     # 從 engine.py 重新生成 fishing.py
```

`fishing.py` 的內容就是 `engine.py` 的 base64，兩份永遠一致、不會分叉。

## License

本專案採用 [PolyForm Noncommercial License 1.0.0](LICENSE)。允許非商業使用、修改和分發；商業使用須另行取得授權。🎣
