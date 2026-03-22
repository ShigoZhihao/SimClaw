# ====================================================================
# test_safety.py — safety.py のテスト
# ====================================================================
# パストラバーサル攻撃への防御が最重要。

import pytest
from pathlib import Path
from simclaw.config import load_config
from simclaw.safety import SafetyGuard, _is_inside

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@pytest.fixture
def guard():
    """SafetyGuard のインスタンスを返すフィクスチャ。"""
    config = load_config(str(CONFIG_PATH))
    return SafetyGuard(config.safety)


# --- _is_inside ヘルパーのテスト ---

def test_is_inside_true():
    """子パスが親ディレクトリの中にある場合 True を返すか。"""
    parent = Path("/home/user/SimClaw/workspace").resolve()
    child = Path("/home/user/SimClaw/workspace/MEMORY.md").resolve()
    assert _is_inside(child, parent) is True


def test_is_inside_false():
    """異なるディレクトリの場合 False を返すか。"""
    parent = Path("/home/user/SimClaw/workspace").resolve()
    other = Path("/etc/passwd").resolve()
    assert _is_inside(other, parent) is False


def test_is_inside_parent_itself():
    """パスが親ディレクトリ自体と同じ場合 True を返すか。"""
    parent = Path("/home/user/SimClaw/workspace").resolve()
    assert _is_inside(parent, parent) is True


# --- validate_read_path のテスト ---

def test_validate_read_path_allowed(tmp_path, guard):
    """許可フォルダ内の既存ファイルは読めるか。"""
    # allowed_read_dirs にある workspace/ 配下にテストファイルを作る
    workspace = Path("/home/user/SimClaw/workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    test_file = workspace / "test_read.txt"
    test_file.write_text("hello")

    result = guard.validate_read_path(str(test_file))
    assert result == test_file.resolve()

    test_file.unlink()  # テスト後に削除


def test_validate_read_path_traversal(guard):
    """パストラバーサル攻撃（../）を拒否するか。"""
    with pytest.raises(PermissionError):
        guard.validate_read_path("./workspace/../../../etc/passwd")


def test_validate_read_path_outside(guard):
    """許可フォルダ外のファイルを拒否するか。"""
    with pytest.raises(PermissionError):
        guard.validate_read_path("/etc/passwd")


def test_validate_read_path_not_found(guard):
    """許可フォルダ内でもファイルが存在しなければエラーか。"""
    with pytest.raises(FileNotFoundError):
        guard.validate_read_path("./workspace/nonexistent_file_xyz.md")


# --- validate_write_path のテスト ---

def test_validate_write_path_allowed(guard):
    """許可フォルダへの書込みパスを通すか（ファイル未存在でもOK）。"""
    result = guard.validate_write_path("./macros/test_macro.java")
    assert result.parent.name == "macros"


def test_validate_write_path_outside(guard):
    """許可フォルダ外への書込みを拒否するか。"""
    with pytest.raises(PermissionError):
        guard.validate_write_path("/tmp/evil.sh")


def test_validate_write_path_traversal(guard):
    """書込みでのパストラバーサルも拒否するか。"""
    with pytest.raises(PermissionError):
        guard.validate_write_path("./macros/../../etc/crontab")
