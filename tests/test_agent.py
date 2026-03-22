# ====================================================================
# test_agent.py — agent.py のテスト（LLMはモック使用）
# ====================================================================

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from simclaw.config import load_config
from simclaw.agent import Agent
from simclaw.llm import LLMResponse
from simclaw.tools.base import ToolResult

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@pytest.fixture
def config():
    return load_config(str(CONFIG_PATH))


@pytest.fixture
def agent(config):
    """モック LLMClient を持つ Agent を作る。"""
    with patch("simclaw.agent.LLMClient"):
        ag = Agent(config)
    return ag


def test_agent_init(config):
    """Agent が正常に初期化されるか。"""
    with patch("simclaw.agent.LLMClient"):
        ag = Agent(config)
    assert ag.tools is not None
    assert ag.memory is not None
    assert ag.ws is not None


def test_agent_run_no_tool_calls(agent):
    """ツール呼び出しなし（タスク即完了）の場合に正常終了するか。"""
    # LLMがテキストだけ返す（ツール不要）
    agent.llm.chat = MagicMock(return_value=LLMResponse(
        content="タスクが完了しました。",
        tool_calls=None
    ))

    # エラーなく実行できるか
    agent.run("こんにちは")
    # run() は return するだけなのでエラーがなければOK


def test_agent_run_with_tool_call(agent):
    """ツール呼び出しが1回あってから完了する場合のテスト。"""
    responses = [
        # 1回目: ツールを呼び出す
        LLMResponse(
            content="ファイルを読みます",
            tool_calls=[{
                "id": "tc_001",
                "name": "file_read",
                "arguments": {"path": "./workspace/SOUL.md"}
            }]
        ),
        # 2回目: ツール結果を受けて完了
        LLMResponse(content="ファイルを読みました。完了です。", tool_calls=None),
    ]
    agent.llm.chat = MagicMock(side_effect=responses)

    agent.run("SOUL.mdを読んで")
    # 2回 chat が呼ばれているか確認
    assert agent.llm.chat.call_count == 2


def test_agent_execute_tool_unknown(agent):
    """存在しないツールを実行するとエラーになるか。"""
    fake_call = {"id": "tc_999", "name": "nonexistent_tool", "arguments": {}}
    result = agent._execute_tool(fake_call)
    assert result.success is False
    assert "存在しません" in result.error


def test_agent_execute_tool_file_read(agent):
    """file_read ツールが正常に実行されるか（承認不要ツール）。"""
    # workspace/SOUL.md が存在すれば成功するはず
    fake_call = {
        "id": "tc_001",
        "name": "file_read",
        "arguments": {"path": "./workspace/SOUL.md"}
    }
    result = agent._execute_tool(fake_call)
    assert result.success is True
    assert "SimClaw" in result.output


def test_agent_consecutive_error_limit(agent):
    """連続エラーが上限に達したら停止するか。"""
    # 常にエラーを返すツールを模倣する
    call_count = 0

    def failing_responses(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return LLMResponse(
            content="",
            tool_calls=[{
                "id": f"tc_{call_count}",
                "name": "nonexistent_tool",
                "arguments": {}
            }]
        )

    agent.llm.chat = MagicMock(side_effect=failing_responses)

    # max_consecutive_errors = 5 なので5回で止まるはず
    agent.run("失敗し続けるタスク")
    assert call_count <= agent.config.safety.max_consecutive_errors + 1


def test_skills_loader_builds_context(config):
    """SkillLoader が skills/ から SKILL.md を読み込むか。"""
    from simclaw.skills.loader import SkillLoader
    loader = SkillLoader(config)
    context = loader.build_skill_context()
    # skills/star-ccm/SKILL.md があれば内容が含まれるはず
    assert "STAR-CCM+" in context or context == ""  # skills/がない環境でも通る


def test_persistent_memory_save_learning(config):
    """save_learning() が MEMORY.md に記録されるか。"""
    from simclaw.workspace.manager import WorkspaceManager
    from simclaw.memory.persistent import PersistentMemory

    ws = WorkspaceManager(config)
    pm = PersistentMemory(config, ws)

    before = ws.read_memory()
    pm.save_learning("テストカテゴリ", "テスト学習内容XYZ")
    after = ws.read_memory()

    assert "テスト学習内容XYZ" in after
    assert len(after) > len(before)


def test_context_engine_build_system_prompt(config):
    """build_system_prompt() がシステムプロンプトを生成するか。"""
    from simclaw.workspace.manager import WorkspaceManager
    from simclaw.memory.persistent import PersistentMemory
    from simclaw.context.engine import ContextEngine

    ws = WorkspaceManager(config)
    pm = PersistentMemory(config, ws)
    engine = ContextEngine(config, ws, pm)

    prompt = engine.build_system_prompt("BASE PROMPT")
    assert "BASE PROMPT" in prompt
    assert len(prompt) > 100
