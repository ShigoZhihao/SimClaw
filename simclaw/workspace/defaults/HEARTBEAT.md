# HEARTBEAT.md — 定期チェック項目

## 毎回のセッション開始時
- [ ] Ollama が起動しているか確認（`ollama list`）
- [ ] STAR-CCM+ のライセンスが有効か確認
- [ ] 前回の作業ログを確認（`memory_search` で検索）

## 週次チェック
- [ ] MEMORY.md の内容を整理・重複削除
- [ ] logs/ フォルダの古いログを削除
- [ ] macros/ フォルダの不要マクロを整理

## エラー時のチェックリスト
1. `log_read` でエラーの詳細を確認
2. `doc_search` でAPI仕様を確認
3. `memory_search` で過去に同じエラーがないか確認
4. マクロを修正して再実行
5. 解決したら `memory_write` で記録
