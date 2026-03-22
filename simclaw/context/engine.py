# ====================================================================
# context/engine.py — コンテキストウィンドウの自動管理
# ====================================================================
#
# 【このファイルは何？】
# LLMに渡せるトークン数には上限がある（コンテキストウィンドウ）。
# 会話が長くなりすぎたとき、古い部分を「要約」して圧縮する。
#
# 【比喩で理解する】
# コンテキストウィンドウ = RAM（速いが小さい）
# MEMORY.md             = ディスク（遅いが大きい）
# このファイル           = OSのメモリ管理（スワップ担当）
#
# 【どう使う？】
# engine = ContextEngine(config, ws, persistent)
# system_prompt = engine.build_system_prompt(base_prompt)
# if engine.should_compress(messages):
#     messages = engine.compress_messages(messages, llm_client)
# ====================================================================


class ContextEngine:
    """コンテキストウィンドウを自動管理するエンジン。"""

    def __init__(self, config, workspace_manager, persistent_memory):
        self.max_tokens = config.context.max_tokens
        self.compress_threshold = config.context.compress_threshold
        self.system_reserve = config.context.system_reserve  # システムプロンプト用の予約量
        self.ws = workspace_manager
        self.persistent = persistent_memory

    def estimate_tokens(self, text):
        """テキストのトークン数を推定する。
        正確なトークナイザーは重いので、文字数÷3で近似する。
        日本語1文字 ≒ 1〜2トークン、英語1単語 ≒ 1〜2トークンのため。
        """
        return len(text) // 3

    def build_system_prompt(self, base_prompt):
        """ワークスペース .md + 直近ログ を base_prompt に結合して返す。

        引数:
            base_prompt: エージェントの基本指示テキスト
        戻り値:
            結合したシステムプロンプト
        """
        # ワークスペースの全 .md を結合する
        workspace_ctx = self.ws.build_system_context()
        full = base_prompt + "\n\n--- ワークスペース ---\n" + workspace_ctx

        # 直近の作業ログを追加する（スペースに余裕がある場合のみ）
        recent = self.persistent.get_recent_context(days=2)
        if recent and self.estimate_tokens(full + recent) < self.system_reserve:
            full += "\n\n--- 直近の作業ログ ---\n" + recent
        elif self.estimate_tokens(full) > self.system_reserve:
            # システムプロンプトが大きすぎる場合は作業ログを省略する
            full += "\n\n（作業ログは省略。memory_search で検索可。）"

        return full

    def should_compress(self, messages):
        """会話履歴の合計トークン数が閾値を超えているか判定する。"""
        total = sum(
            self.estimate_tokens(str(m.get("content", "")))
            for m in messages
        )
        return total > self.compress_threshold

    def compress_messages(self, messages, llm_client):
        """古い会話を要約して圧縮する。

        引数:
            messages: 現在の会話履歴
            llm_client: LLMClient（要約生成に使う）
        戻り値:
            圧縮後の会話履歴
        """
        # system メッセージと非systemメッセージに分ける
        system_msgs = [m for m in messages if m["role"] == "system"]
        other_msgs = [m for m in messages if m["role"] != "system"]

        # 10件以下なら圧縮不要
        if len(other_msgs) <= 10:
            return messages

        # 古い部分（直近10件を除く）を要約対象にする
        old_msgs = other_msgs[:-10]
        recent_msgs = other_msgs[-10:]

        # LLMで古い会話を要約する
        old_text = "\n".join(
            f"[{m['role']}]: {str(m.get('content', ''))[:300]}"
            for m in old_msgs
        )
        try:
            resp = llm_client.chat([
                {"role": "system", "content": "以下の会話履歴を200文字以内で要約してください。"},
                {"role": "user", "content": old_text[:3000]}
            ])
            summary = resp.content
        except Exception:
            # 要約に失敗した場合は汎用テキストで代替する
            summary = "（前の会話は省略されました）"

        # 要約をメモリに保存する
        self.persistent.save_learning("会話要約", summary)

        # 要約メッセージ + 直近10件に置き換える
        return (
            system_msgs
            + [{"role": "assistant", "content": f"[前の会話の要約]: {summary}"}]
            + recent_msgs
        )
