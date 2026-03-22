# TOOLS.md — 環境メモ

## STAR-CCM+ 環境
- 実行ファイル: config.yaml の starccm.executable を参照
- ライセンス: 環境変数 CDLMD_LICENSE_FILE
- 並列数: config.yaml の starccm.default_args を参照

## ローカルLLM
- Ollama: http://localhost:11434
- 使用モデル: config.yaml の llm.model を参照
- 起動確認: `ollama serve` → `ollama list`

## Python 環境
- Python 3.10+
- 依存関係: pyproject.toml 参照
- インストール: `pip install -e .`

## よく使うコマンド
```bash
# ドキュメント取込み
python -m simclaw index --docs-dir ./docs

# エージェント起動
python -m simclaw run

# 単発タスク実行
python -m simclaw run --task "○○を解析するマクロを作成して"
```
