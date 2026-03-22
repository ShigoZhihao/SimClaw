# AGENTS.md — SimClawの操作マニュアル

## 利用可能なツール

### ドキュメント・検索
- `doc_search(query)` — STAR-CCM+ ドキュメントをRAG検索
- `web_search(query)` — DuckDuckGo でWeb検索
- `browser_fetch(url)` — 許可ドメインのWebページを取得

### ファイル操作
- `file_read(path)` — 許可フォルダのファイルを読む
- `file_write(path, content)` — 許可フォルダにファイルを書く

### STAR-CCM+ 操作
- `star_macro_write(filename, content)` — macros/ にマクロを書き出す
- `star_execute(macro_path)` — マクロをバッチ実行（人間承認必須）
- `log_read(log_path)` — ログを読んでエラーを抽出

### シェル（読み取り専用系）
- `shell_execute(command)` — ls, cat, head, tail, find, grep, diff, wc のみ

### メモリ
- `memory_search(query)` — 過去の経験をハイブリッド検索
- `memory_write(category, content)` — MEMORY.md に記録

## ワークフロー（標準手順）

```
1. memory_search → 過去に似た問題を解いたか確認
2. doc_search → 使うAPIを確認
3. star_macro_write → マクロを書く
4. star_execute → 実行（承認後）
5. log_read → 結果確認（エラーがあれば解析）
6. memory_write → 学んだことを記録
```

## 注意事項
- star_execute は人間の承認が必要
- 外部クラウドAPIへの接続は禁止
- 許可フォルダ外へのアクセスは禁止
