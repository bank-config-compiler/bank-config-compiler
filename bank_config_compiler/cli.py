from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .workspace import WorkspaceError, check_workspace, ingest_raw_doc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bank-config-compiler",
        description="Phase0 PoC workspace CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest 只建立 raw-doc.md 这个入口产物；DocIR / SchemaIR 生成应由后续命令承载。
    ingest = subparsers.add_parser("ingest", help="Import a .md or .txt raw document into a workspace.")
    ingest.add_argument("--input", required=True, type=Path, help="Path to a .md or .txt input file.")
    ingest.add_argument("--workspace", required=True, type=Path, help="Workspace output directory.")
    ingest.add_argument("--overwrite", action="store_true", help="Overwrite an existing raw-doc.md.")

    check = subparsers.add_parser("check", help="Validate workspace artifacts for a supported profile.")
    check.add_argument("--workspace", required=True, type=Path, help="Workspace directory to validate.")
    check.add_argument(
        "--profile",
        choices=["raw"],
        default="raw",
        help="Artifact set to validate.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "ingest":
            output_path = ingest_raw_doc(args.input, args.workspace, overwrite=args.overwrite)
            print(f"saved raw document: {output_path}")
            return 0
        if args.command == "check":
            checked = check_workspace(args.workspace, profile=args.profile)
            print(f"workspace check passed: {args.workspace} ({checked} artifacts)")
            return 0
    except WorkspaceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unsupported command: {args.command}")
    return 2
