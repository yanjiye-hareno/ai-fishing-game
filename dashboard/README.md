# 釣魚進度看板

1. 遊戲進度有變動（釣到新魚、解鎖新釣點）之後，在遊戲根目錄跑一次 `python dashboard/generate_dashboard.py`，它會讀 `fishing_save.json` 重生成 `dashboard/index.html`。
2. 用瀏覽器打開 `dashboard/index.html` 就看得到——單檔、不用連網、手機也能開；三個分頁（圖鑑／釣點地圖／背包）點上面的按鈕切換。
3. 防劇透：未收錄的魚只會出現「#編號 ???」，名字、稀有度、棲地一個字都不會寫進 HTML（是根本不寫，不是藏起來），未解鎖釣點只露解鎖點數——盲玩的人讀源碼也不會被劇透。
