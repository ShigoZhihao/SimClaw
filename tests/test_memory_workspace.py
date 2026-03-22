# ====================================================================
# test_memory_workspace.py — conversation.py と workspace/manager.py のテスト
# ====================================================================

import pytest
from pathlib import Path
from simclaw.config import load_config
from simclaw.memory.conversation import ConversationMemory
from simclaw.workspace.manager import WorkspaceManager

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@pytest.fixture
def config():
    return load_config(str(CONFIG_PATH))


# --- ConversationMemory のテスト ---

def test_conversation_add_and_get():
    """メッセージを追加して取得できるか。"""
    mem = ConversationMemory(max_messages=10)
    mem.add("user", "こんにちは")
    mem.add("assistant", "こんにちは！")
    msgs = mem.get_messages()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["content"] == "こんにちは！"


def test_conversation_trim():
    """max_messages を超えたら古いメッセージが削除されるか。"""
    mem = ConversationMemory(max_messages=5)
    for i in range(10):
        mem.add("user", f"メッセージ{i}")
    msgs = mem.get_messages()
    # system以外で5件だけ残るはず
    assert len(msgs) <= 5


def test_conversation_system_preserved():
    """system メッセージは削除されないか。"""
    mem = ConversationMemory(max_messages=3)
    mem.add("system", "あなたはSimClawです")
    for i in range(5):
        mem.add("user", f"メッセージ{i}")
    msgs = mem.get_messages()
    # system は必ず残る
    system_msgs = [m for m in msgs if m["role"] == "system"]
    assert len(system_msgs) == 1
    assert system_msgs[0]["content"] == "あなたはSimClawです"


def test_conversation_add_tool_calls():
    """ツール呼び出しメッセージが正しく記録されるか。"""
    mem = ConversationMemory()
    tool_calls = [{"id": "tc_001", "name": "file_read", "arguments": {"path": "./test.txt"}}]
    mem.add_tool_calls("ファイルを読みます", tool_calls)
    msgs = mem.get_messages()
    assert len(msgs) == 1
    assert msgs[0]["role"] == "assistant"
    assert "tool_calls" in msgs[0]
    assert msgs[0]["tool_calls"][0]["function"]["name"] == "file_read"


def test_conversation_add_tool_result():
    """ツール結果を tool ロールで追加できるか。"""
    mem = ConversationMemory()
    mem.add("tool", "ファイルの内容です", tool_call_id="tc_001", name="file_read")
    msgs = mem.get_messages()
    assert msgs[0]["role"] == "tool"
    assert msgs[0]["tool_call_id"] == "tc_001"
    assert msgs[0]["name"] == "file_read"


def test_conversation_clear_non_system():
    """clear_non_system() が system 以外を削除するか。"""
    mem = ConversationMemory()
    mem.add("system", "システムプロンプト")
    mem.add("user", "ユーザー入力")
    mem.add("assistant", "応答")
    mem.clear_non_system()
    msgs = mem.get_messages()
    assert len(msgs) == 1
    assert msgs[0]["role"] == "system"


# --- WorkspaceManager のテスト ---

def test_workspace_manager_creates_files(config):
    """WorkspaceManager 初期化時に .md ファイルが作られるか。"""
    ws = WorkspaceManager(config)
    soul = ws.read_soul()
    # SOUL.md の内容が空でないか
    assert len(soul) > 0
    assert "SimClaw" in soul


def test_workspace_manager_read_file(config):
    """read_file() が正しく動くか。"""
    ws = WorkspaceManager(config)
    memory = ws.read_memory()
    assert "MEMORY" in memory or "記憶" in memory


def test_workspace_manager_append_memory(config):
    """append_memory() が MEMORY.md に追記するか。"""
    ws = WorkspaceManager(config)
    before = ws.read_memory()
    ws.append_memory("テスト学習: これはテストです")
    after = ws.read_memory()
    assert "テスト学習" in after
    assert len(after) > len(before)


def test_workspace_manager_write_daily_log(config, tmp_path):
    """write_daily_log() が日次ログに追記するか。"""
    ws = WorkspaceManager(config)
    ws.write_daily_log("テストログエントリ")
    # ログファイルが作られたか確認
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = Path(config.memory.daily_log_dir) / f"{today}.md"
    assert log_path.exists()
    content = log_path.read_text()
    assert "テストログエントリ" in content


def test_workspace_manager_build_system_context(config):
    """build_system_context() が全ファイルを結合するか。"""
    ws = WorkspaceManager(config)
    context = ws.build_system_context()
    # 主要なファイル名が含まれているか確認
    assert "SOUL.md" in context
    assert "MEMORY.md" in context
