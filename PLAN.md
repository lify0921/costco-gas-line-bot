# コストコ久山ガソリン価格BOT 拡張プラン

## ゴール
1. ご近所さんも受信できるよう **LINE broadcast 配信**に切り替える
2. **価格変動があった日だけ通知**する（毎日同じ価格の邪魔通知をなくす）
3. スクレイピングの信頼性を上げ、**既存の致命バグを修正**する
4. cron実行時刻を gogo.gs の投稿タイミングに合わせて最適化

## 使うツール・ライブラリ
- 既存の `requests`, `BeautifulSoup`, `matplotlib` のみ（追加なし）
- GitHub Actions（既存の `.github/workflows/daily-price.yml` を修正）

## 制約・前提
- LINE無料枠: 月200通（宛先数のみでカウント、メッセージオブジェクト数は無関係）
- 想定: 6人 × 変動日のみ（月20日程度）= **月120通前後**で無料枠内
- gogo.gs は 7時台投稿が多い → **9:30 JST実行**が最適

## ステップ

### Step 1: 致命バグ修正（main.py）
- **問題**: スクレイピング失敗時に「前日価格」を今日の価格としてCSVに書き込んでcommitしている → 変動検知が狂う
- **対応**: 失敗時はCSVに書き込まず、通知の `note` 表示のみに留める

### Step 2: 「前回通知価格」の永続化
- 新ファイル `data/last_notified.json` を作成
- `{"date": "2026-04-13", "price": 151.0}` の形式で最後に **通知した** 価格を記録
- CSV（gogo.gs履歴）とは独立管理（過去バックフィルの影響を受けないため）

### Step 3: scraper.py ロバスト化
- `scrape_current_price()`: 日付セルもパースして **最新日付の行のみ採用**
- `PRICE_MIN/MAX` を 100-250 → **80-300** に緩和
- 価格regexを「円」直前の数字に限定して誤抽出を防ぐ
- 投稿時刻（例: `7時`）も取得し、通知に含める

### Step 4: line_bot.py を broadcast 化
- エンドポイント: `/v2/bot/message/push` → **`/v2/bot/message/broadcast`**
- body から `to` 削除、`LINE_USER_ID` 参照も削除
- 429/5xx 時の指数バックオフリトライ（1〜2回）

### Step 5: 変動チェックロジック（main.py）
- 今日の価格を取得 → `last_notified.json` の価格と比較
- **同じなら通知スキップ、CSVは更新**（履歴は残す）
- **違えば broadcast 通知 + `last_notified.json` 更新**
- 初回（ファイル無し）は必ず通知
- スクレイピング失敗時は通知せず、翌日に持ち越し

### Step 6: GitHub Actions 改修
- cron: `3 23 * * *`（08:03 JST）→ **`30 0 * * *`（09:30 JST）**
- `git push` 前に `git pull --rebase` 追加
- push 失敗時のリトライ（1回）

## 完了条件
- [ ] main.pyの失敗時CSV汚染バグが修正されている
- [ ] `last_notified.json` が作成され、変動日のみ通知される
- [ ] broadcast APIへの切替が動作（ご近所さん友だち追加で配信される）
- [ ] cron実行時刻が 09:30 JST
- [ ] scraper.py が日付チェック・範囲拡大・regex厳密化されている
- [ ] 手動トリガー（workflow_dispatch）で一度動作確認して正常動作

## 運用ドキュメント（別途口頭共有）
- LINE Official Account Manager から友だち追加QRコード/IDを取得
- ご近所さんに配って友だち追加してもらう
- 友だち数が月200/変動日数 を超えそうなら有料プラン（ライト ¥5,000/月 5,000通）へ

## 見送る事項（今回はやらない）
- graph.py の描画改善（動作に影響なし、後回し）
- Flex Message 化（現状のテキスト+画像で十分）
- 有料プラン移行（まずは無料で運用開始）
