# ====================================================================
# main.py — CLIエントリーポイント
# ====================================================================
#
# 【使い方】
# python -m simclaw index           ← ドキュメント取込み
# python -m simclaw run             ← 対話モードで起動
# python -m simclaw run --task "○○" ← 単発タスク実行
# ====================================================================

import argparse
from rich.console import Console
from simclaw.config import load_config
from simclaw.agent import Agent

console = Console()


def cmd_index(args):
    """ドキュメントをRAGインデックスに取り込む。"""
    config = load_config(args.config)
    docs_dir = args.docs_dir or config.rag.docs_dir

    console.print(f"[bold]ドキュメント取込み開始: {docs_dir}[/]")
    console.print("[dim]Embeddingモデル読込み中（初回は数分かかります）...[/]")

    try:
        from simclaw.rag.indexer import DocumentIndexer
        indexer = DocumentIndexer(config)
        result = indexer.index_directory(docs_dir)
        console.print(
            f"[green]完了: {result['indexed_files']} ファイル, "
            f"{result['total_chunks']} チャンク[/]"
        )
    except Exception as e:
        console.print(f"[red]取込みエラー: {e}[/]")
        raise


def cmd_run(args):
    """エージェントを起動する。"""
    config = load_config(args.config)
    agent = Agent(config)

    # RAGを有効化する（ドキュメントがある場合のみ）
    try:
        from simclaw.rag.retriever import Retriever
        agent.setup_rag(Retriever(config))
        console.print("[dim]RAG有効（doc_search 使用可）[/]")
    except Exception as e:
        console.print(
            f"[yellow]RAG無効（{e}）\n"
            f"  先に 'python -m simclaw index' でドキュメントを取り込んでください。[/]"
        )

    # 単発タスクモード
    if args.task:
        agent.run(args.task)
        return

    # 対話モード
    console.print("\n[bold green]SimClaw 起動[/]")
    console.print("[dim]終了するには: quit / exit / 終了 / Ctrl+C[/]\n")

    while True:
        try:
            user_input = console.input("[green]あなた > [/]").strip()

            # 終了コマンドの確認
            if user_input.lower() in ["quit", "exit", "終了", "q"]:
                console.print("[dim]SimClaw を終了します。[/]")
                break

            # 空入力は無視する
            if not user_input:
                continue

            agent.run(user_input)

        except KeyboardInterrupt:
            console.print("\n[dim]Ctrl+C で終了します。[/]")
            break


def main():
    """メインエントリーポイント。"""
    parser = argparse.ArgumentParser(
        description="SimClaw — STAR-CCM+ 特化 自律CAEエージェント",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python -m simclaw index                   ドキュメント取込み
  python -m simclaw index --docs-dir ./docs ドキュメント取込み（パス指定）
  python -m simclaw run                     対話モード起動
  python -m simclaw run --task "メッシュ設定マクロを作成して"
        """
    )
    parser.add_argument(
        "--config", default="config.yaml",
        help="設定ファイルのパス（デフォルト: config.yaml）"
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # index サブコマンド
    index_parser = subparsers.add_parser("index", help="ドキュメントをRAGに取込む")
    index_parser.add_argument("--docs-dir", default=None, help="ドキュメントフォルダのパス")

    # run サブコマンド
    run_parser = subparsers.add_parser("run", help="エージェントを起動する")
    run_parser.add_argument("--task", default=None, help="実行するタスク（省略で対話モード）")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
