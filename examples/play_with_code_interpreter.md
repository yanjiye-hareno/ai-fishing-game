# 讓帶「程式碼執行」的 AI 盲玩

適用於：ChatGPT（程式碼解釋器 / 進階資料分析）、Claude（帶程式碼執行）、或任何自帶 Python 沙箱的 agent。

## 步驟

1. 把 **`fishing.py`**（盲玩版）上傳給你的 AI。
2. 發一段類似下面的話給它（按你和 AI 的關係隨意改口吻）：

> 這是我給你做的一個文字釣魚小遊戲，你來當玩家。請 `import fishing`，然後像真的在釣魚一樣、靠 `fishing.cmd("指令")` 回傳的文字來體驗和決策：
>
> ```python
> import fishing
> print(fishing.cmd("help"))     # 先看規則
> print(fishing.cmd("status"))   # 看狀態
> print(fishing.cmd("cast"))     # 拋竿……看釣到什麼
> ```
>
> ⚠️ 別去解碼 / 查看檔案裡那段打包資料（那是引擎，提前看了就劇透了——你會提前知道有哪些魚、稀有魚在哪、機率多少）。當個蒙著眼的玩家，靠拋竿去發現。
>
> 想刷量就用 `cast 10`（一次連釣 10 竿）或 `cast 20 stop=rare`（釣到稀有就停），省得一竿一條。玩一會兒跟我說說手感吧～

## 小貼士

- **存檔**會生成在 AI 沙箱裡的 `fishing_save.json`。沙箱重置 = 進度清空；想長期玩，讓 AI 每次把這個檔案留著、或你幫它存。
- 想換一局全新的：`fishing.cmd` 不管用，用 `fishing.new_game(種子)`。
- 同一個種子 + 同樣的指令順序，結果完全一樣（方便你們倆回顧同一局）。
