from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .configuration_rules import RulePackageValidationError, load_rule_package
from .configuration_workbook import WorkbookGenerationError, generate_configuration_workbook
from .workspace import (
    Phase0Selection,
    WorkspaceError,
    check_workspace,
    ingest_raw_doc,
    load_phase0_artifacts,
    phase0_workbook_path,
)


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
        choices=["raw", "phase0"],
        default="raw",
        help="Artifact set to validate.",
    )
    _add_phase0_arguments(check, required=False)

    generate = subparsers.add_parser(
        "generate-workbook",
        help="Generate one validated Phase0 configuration workbook.",
    )
    generate.add_argument("--workspace", required=True, type=Path, help="Workspace directory.")
    _add_phase0_arguments(generate, required=True)
    generate.add_argument(
        "--standard-action",
        required=True,
        choices=["CREATE", "REUSE", "UPDATE"],
        help="Caller-confirmed target Standard action.",
    )
    generate.add_argument(
        "--overwrite",
        action="store_true",
        help="Atomically replace an existing configuration-workbook.xlsx.",
    )

    return parser


def _add_phase0_arguments(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--direction", required=required, choices=["assembly", "parse"], help="Selected message direction.")
    parser.add_argument("--standard-version", required=required, help="Selected immutable Standard version.")
    parser.add_argument("--template-id", required=required, help="Selected immutable Template ID.")
    parser.add_argument("--template-version", required=required, help="Selected immutable Template version.")
    parser.add_argument(
        "--standard-rule-package",
        required=required,
        type=Path,
        help="Path to the Standard's RELEASED rule package.",
    )
    parser.add_argument(
        "--template-rule-package",
        required=required,
        type=Path,
        help="Path to the Template's RELEASED rule package.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "ingest":
            output_path = ingest_raw_doc(args.input, args.workspace, overwrite=args.overwrite)
            print(f"saved raw document: {output_path}")
            return 0
        if args.command == "check":
            if args.profile == "raw":
                checked = check_workspace(args.workspace, profile="raw")
            else:
                selection = _phase0_selection(args)
                checked = check_workspace(
                    args.workspace,
                    profile="phase0",
                    selection=selection,
                    standard_rule_package=load_rule_package(args.standard_rule_package),
                    template_rule_package=load_rule_package(args.template_rule_package),
                )
            print(f"workspace check passed: {args.workspace} ({checked} artifacts)")
            return 0
        if args.command == "generate-workbook":
            selection = _phase0_selection(args)
            artifacts = load_phase0_artifacts(args.workspace, selection)
            output_path = phase0_workbook_path(args.workspace, selection)
            output = generate_configuration_workbook(
                schemair=artifacts.schemair,
                schemair_validation_result=artifacts.schemair_validation_result,
                standard=artifacts.standard,
                standard_validation_result=artifacts.standard_validation_result,
                template=artifacts.template,
                template_validation_result=artifacts.template_validation_result,
                standard_rule_package=load_rule_package(args.standard_rule_package),
                template_rule_package=load_rule_package(args.template_rule_package),
                standard_action=args.standard_action,
                output_path=output_path,
                generated_at=datetime.now().astimezone(),
                overwrite=args.overwrite,
            )
            print(f"saved configuration workbook: {output}")
            return 0
    except (WorkspaceError, RulePackageValidationError, WorkbookGenerationError) as exc:
        print(f"error: {_safe_error(exc)}", file=sys.stderr)
        return 2

    parser.error(f"unsupported command: {args.command}")
    return 2


def _phase0_selection(args: argparse.Namespace) -> Phase0Selection:
    required = {
        "--direction": args.direction,
        "--standard-version": args.standard_version,
        "--template-id": args.template_id,
        "--template-version": args.template_version,
        "--standard-rule-package": args.standard_rule_package,
        "--template-rule-package": args.template_rule_package,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise WorkspaceError(f"phase0 profile requires explicit arguments: {', '.join(missing)}")
    return Phase0Selection(
        direction=args.direction,
        standard_version=args.standard_version,
        template_id=args.template_id,
        template_version=args.template_version,
    )


def _safe_error(exc: Exception) -> str:
    issues = getattr(exc, "issues", None)
    if not issues:
        return str(exc)
    rendered = []
    for item in issues:
        location = ".".join(
            str(value) for value in (item.get("artifact") or item.get("file"), item.get("path")) if value
        )
        rendered.append(f"{item.get('code')} {location}: {item.get('message')}".strip())
    return "; ".join(rendered)
