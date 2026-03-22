# ====================================================================
# agent.py — SimClawエージェントの頭脳（最重要ファイル）
# ====================================================================
#
# 【このファイルは何？】
# ReActパターン（推論 → 行動 → 観察 → 推論…）で動くエージェントループ。
# 「考える → ツールを使う → 結果を見る → また考える」を繰り返す。
#
# 【ReActパターンとは？】
# Re(asoning) + Act(ion) の略。
# 1. Reason: LLMが「次に何をすべきか」を考える
# 2. Act: ツールを実行する
# 3. Observe: ツールの結果を見る
# 4. また1に戻る（完了するまで）
#
# 【どう使う？】
# agent = Agent(config)
# agent.run("メッシュ設定マクロを作成して")
# ====================================================================

import json
from rich.console import Console
from rich.prompt import Confirm

from simclaw.llm import LLMClient
from simclaw.memory.conversation import ConversationMemory
from simclaw.memory.persistent import PersistentMemory
from simclaw.context.engine import ContextEngine
from simclaw.workspace.manager import WorkspaceManager
from simclaw.skills.loader import SkillLoader
from simclaw.tools import ToolRegistry
from simclaw.tools.base import ToolResult


# エージェントの基本指示（英語の方がLLMの精度が高いため英語で書く）
BASE_SYSTEM_PROMPT = """You are SimClaw, an autonomous CAE engineer agent specialized in
Siemens STAR-CCM+ simulation software.

Your workflow:
1. RESEARCH: Use doc_search to find correct API calls BEFORE writing macros
2. WRITE: Use star_macro_write to create the macro
3. EXECUTE: Use star_execute to run it (human approval required)
4. DIAGNOSE: If failed, use log_read then doc_search to find the cause
5. FIX: Revise the macro and retry
6. LEARN: Use memory_write to save what you learned

Rules:
- Always doc_search BEFORE writing macros
- Write complete, compilable macros (not fragments)
- After failure, ALWAYS read the log first before fixing
- Explain your reasoning in Japanese
- Use memory_search to check if you solved similar problems before

Available tools will be listed separately.
"""


class Agent:
    """SimClaw の自律エージェント。ReActパターンで動作する。"""

    def __init__(self, config):
        self.config = config

        # 各コンポーネントを初期化する
        self.llm = LLMClient(config.llm)
        self.ws = WorkspaceManager(config)
        self.persistent = PersistentMemory(config, self.ws)
        self.context_engine = ContextEngine(config, self.ws, self.persistent)
        self.skill_loader = SkillLoader(config)
        self.memory = ConversationMemory(config.memory.max_conversation_messages)
        self.tools = ToolRegistry(config)

        # 表示用コンソール（色付き出力）
        self.console = Console()
        # 連続エラー数のカウンター（上限を超えたら停止する）
        self.consecutive_errors = 0

    def setup_rag(self, retriever):
        """RAGを有効化する。doc_search ツールが使えるようになる。

        引数:
            retriever: Retriever オブジェクト
        """
        from simclaw.memory.search import HybridSearch
        hs = HybridSearch(self.config)
        self.tools = ToolRegistry(
            self.config,
            retriever=retriever,
            hybrid_search=hs,
            workspace_manager=self.ws,
            persistent_memory=self.persistent,
        )

    def run(self, task):
        """タスクを受け取り、完了まで自律実行する。

        引数:
            task: ユーザーからの指示（日本語OK）
        """
        # --- システムプロンプトを構築する ---
        # BASE_SYSTEM_PROMPT + スキル + ワークスペース.md + 直近ログ
        base = BASE_SYSTEM_PROMPT
        skill_ctx = self.skill_loader.build_skill_context()
        if skill_ctx:
            base += "\n\n--- Skills ---\n" + skill_ctx

        system_prompt = self.context_engine.build_system_prompt(base)

        # 会話履歴をリセットしてシステムプロンプトとタスクを追加する
        self.memory.clear_non_system()
        self.memory.add("system", system_prompt)
        self.memory.add("user", task)

        self.console.print(f"\n[bold green]タスク:[/] {task}\n")

        # --- ReActループ（最大30ステップ） ---
        for iteration in range(30):
            self.console.print(f"[dim]--- ステップ {iteration + 1} ---[/]")

            messages = self.memory.get_messages()

            # コンテキストが大きすぎる場合は圧縮する
            if self.context_engine.should_compress(messages):
                self.console.print("[dim]コンテキスト圧縮中...[/]")
                messages = self.context_engine.compress_messages(messages, self.llm)
                self.memory.messages = messages

            # LLMに送信して応答を受け取る
            try:
                response = self.llm.chat(
                    messages,
                    tools=self.tools.get_tool_definitions()
                )
            except ConnectionError as e:
                self.console.print(f"[red]LLM接続エラー: {e}[/]")
                return

            # --- ツール呼び出しがある場合 ---
            if response.tool_calls:
                # ツール呼び出しを会話履歴に記録する
                self.memory.add_tool_calls(response.content, response.tool_calls)

                # LLMのテキスト応答があれば表示する
                if response.content:
                    self.console.print(f"[blue]SimClaw:[/] {response.content}")

                # 各ツールを順番に実行する
                turn_results = []
                for tool_call in response.tool_calls:
                    result = self._execute_tool(tool_call)
                    turn_results.append(result)

                    # ツールの結果を会話履歴に追加する
                    result_text = result.output if result.success else f"ERROR: {result.error}"
                    self.memory.add(
                        "tool", result_text,
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"]
                    )

                    # エラーカウンターを更新する
                    if result.success:
                        self.consecutive_errors = 0
                    else:
                        self.consecutive_errors += 1
                        if self.consecutive_errors >= self.config.safety.max_consecutive_errors:
                            self.console.print(
                                f"[red]連続エラー {self.consecutive_errors} 回。安全のため停止します。[/]"
                            )
                            return

                # 日次ログに記録する
                self.persistent.on_turn_end(response.content or "", turn_results)

            # --- ツール呼び出しなし = タスク完了 ---
            else:
                self.memory.add("assistant", response.content)
                self.console.print(f"\n[blue]SimClaw:[/] {response.content}\n")
                self.persistent.on_turn_end(response.content, [])
                return

        # 30ステップに達しても終わらなかった場合
        self.console.print("[yellow]最大ステップ数（30）に達しました。タスクを分割してみてください。[/]")

    def _execute_tool(self, tool_call):
        """ツールを実行する。要承認ツールは確認を求める。

        引数:
            tool_call: {"id": ..., "name": ..., "arguments": {...}}
        戻り値:
            ToolResult
        """
        name = tool_call["name"]
        args = tool_call["arguments"]

        # ツール名と引数を表示する
        args_preview = json.dumps(args, ensure_ascii=False)[:200]
        self.console.print(f"  [yellow]ツール実行:[/] {name}({args_preview})")

        # 人間の承認が必要なツールは確認を求める
        if name in self.config.safety.require_human_approval:
            self.console.print(f"  [red bold]⚠️  承認が必要: {name}[/]")
            approved = Confirm.ask("  実行を許可しますか？")
            if not approved:
                return ToolResult(
                    success=False, output="",
                    error="ユーザーが実行を拒否しました"
                )

        # ツールを実行する
        result = self.tools.execute(name, **args)

        # 結果のステータスを表示する
        if result.success:
            preview = (result.output or "")[:200]
            self.console.print(f"  [green]成功:[/] {preview}")
        else:
            self.console.print(f"  [red]失敗:[/] {result.error[:200]}")

        return result
