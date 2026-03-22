# ====================================================================
# safety.py — セキュリティの門番
# ====================================================================
#
# 【このファイルは何？】
# すべてのファイル読み書きとコマンド実行がこのファイルを通る。
# 原則: ホワイトリスト方式（許可したものだけ通す）
#
# 【なぜ必要？】
# LLMが生成するパスには ../ （親フォルダへの移動）が含まれる恐れがある。
# 例: "../../../etc/passwd" → OSのパスワードファイルを読もうとしている！
# resolve() で絶対パスに変換してから判定することで防御する。
#
# 【どう使う？】
# guard = SafetyGuard(config.safety)
# safe_path = guard.validate_read_path("./workspace/MEMORY.md")
# → OKなら安全な絶対パスを返す。NGならPermissionError。
# ====================================================================

from pathlib import Path


class SafetyGuard:
    """ファイルアクセスとコマンド実行を制限する門番。"""

    def __init__(self, config):
        # allowed_read_dirs を絶対パスに変換して保存
        # resolve() で ../ やシンボリックリンクを解決して正規化する
        self.allowed_read_dirs = [Path(d).resolve() for d in config.allowed_read_dirs]
        self.allowed_write_dirs = [Path(d).resolve() for d in config.allowed_write_dirs]

    def validate_read_path(self, path_str):
        """読取りが許可されているか検証する。

        引数:
            path_str: 検証するファイルパス（文字列）
        戻り値:
            解決済みの絶対 Path オブジェクト
        エラー:
            PermissionError: 許可フォルダ外へのアクセス
            FileNotFoundError: ファイルが存在しない
        """
        # resolve() で ../ やシンボリックリンクを解決して絶対パスにする
        # これによりパストラバーサル攻撃を防ぐ
        resolved = Path(path_str).resolve()

        # いずれかの許可フォルダの中にあるか確認
        is_allowed = any(_is_inside(resolved, d) for d in self.allowed_read_dirs)
        if not is_allowed:
            raise PermissionError(
                f"アクセス拒否: {path_str}\n"
                f"許可フォルダ: {[str(d) for d in self.allowed_read_dirs]}"
            )

        # ファイルの存在確認
        if not resolved.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {path_str}")

        return resolved

    def validate_write_path(self, path_str):
        """書込みが許可されているか検証する。
        ファイルが存在しなくてもOK（新規作成のため）。

        引数:
            path_str: 検証するファイルパス（文字列）
        戻り値:
            解決済みの絶対 Path オブジェクト
        エラー:
            PermissionError: 許可フォルダ外への書込み
        """
        resolved = Path(path_str).resolve()

        is_allowed = any(_is_inside(resolved, d) for d in self.allowed_write_dirs)
        if not is_allowed:
            raise PermissionError(
                f"書込み拒否: {path_str}\n"
                f"許可フォルダ: {[str(d) for d in self.allowed_write_dirs]}"
            )
        return resolved

    def validate_starccm_command(self, cmd_list, starccm_config):
        """starccm+ 以外のプログラム実行を拒否する。

        引数:
            cmd_list: 実行コマンドのリスト（例: ["/opt/.../starccm+", "-batch", ...]）
            starccm_config: StarCCMConfig オブジェクト
        エラー:
            PermissionError: 許可されていないプログラムの実行
        """
        if not cmd_list:
            raise PermissionError("空のコマンドは実行できません")

        # 実行ファイルのパスを絶対パスに変換して比較する
        executable = Path(cmd_list[0]).resolve()
        allowed = Path(starccm_config.executable).resolve()

        if executable != allowed:
            raise PermissionError(
                f"実行拒否: {cmd_list[0]}\n"
                f"許可プログラム: {starccm_config.executable}"
            )


def _is_inside(path, parent_dir):
    """pathがparent_dirの中にあるか判定するヘルパー関数。

    例:
        _is_inside(Path("/workspace/MEMORY.md"), Path("/workspace")) → True
        _is_inside(Path("/etc/passwd"), Path("/workspace"))          → False
    """
    try:
        # relative_to() はpathがparent_dirの配下でなければ ValueError を投げる
        path.relative_to(parent_dir)
        return True
    except ValueError:
        return False
