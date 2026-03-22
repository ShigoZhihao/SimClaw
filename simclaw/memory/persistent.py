# ====================================================================
# memory/persistent.py — 永続メモリ（Markdown on Disk）
# ====================================================================
#
# 【このファイルは何？】
# エージェントの「経験」をディスクに保存する。
# MEMORY.md = 長期記憶、memory/YYYY-MM-DD.md = 日次ログ。
#
# 【ConversationMemory との違い】
# ConversationMemory: 今のセッション中だけの短期記憶（RAM）
# PersistentMemory: セッションをまたいで残る長期記憶（ディスク）
#
# 【どう使う？】
# pm = PersistentMemory(config, ws)
# pm.on_turn_end("応答テキスト", [result1, result2])  # 1ターン終了時
# pm.save_learning("成功パターン", "PolyhederalMesherはこう使う")
# ====================================================================

from pathlib import Path
from datetime import datetime


class PersistentMemory:
    """永続メモリ（ディスクへの書き込み）を管理する。"""

    def __init__(self, config, workspace_manager):
        self.config = config
        self.ws = workspace_manager
        self._turn_count = 0  # セッション内のターン数を数える

    def on_turn_end(self, assistant_message, tool_results=None):
        """1ターン終了時に日次ログへ記録する。

        引数:
            assistant_message: LLMの応答テキスト
            tool_results: そのターンで実行したツールの結果リスト
        """
        self._turn_count += 1

        # 日次ログに書き込む内容を組み立てる
        parts = [f"**アシスタント:** {assistant_message[:500]}"]

        if tool_results:
            for tr in tool_results:
                status = "OK" if tr.success else "NG"
                summary = tr.output[:200] if tr.output else tr.error[:200]
                parts.append(f"  [{status}] {summary}")

        self.ws.write_daily_log("\n".join(parts))

    def save_learning(self, category, content):
        """MEMORY.md に知識を記録する。

        引数:
            category: カテゴリ（例: "成功パターン"）
            content: 記録する内容
        """
        self.ws.append_memory(f"**[{category}]** {content}")

    def get_recent_context(self, days=3):
        """直近N日の作業ログを取得する。

        引数:
            days: 取得する日数
        戻り値:
            ログ内容を結合した文字列（なければ空文字）
        """
        log_dir = Path(self.config.memory.daily_log_dir)
        if not log_dir.exists():
            return ""

        # 日付順（新しい順）にソートして上位N件を取得する
        log_files = sorted(log_dir.glob("*.md"), reverse=True)[:days]
        sections = []
        for f in log_files:
            content = f.read_text(encoding="utf-8")
            sections.append(f"=== {f.stem} ===\n{content}")

        return "\n\n".join(sections)
