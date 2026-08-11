from __future__ import annotations

import argparse
import io
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

from .configuration_rules import RulePackageValidationError, load_rule_package
from .configuration_workbook import WorkbookGenerationError, generate_configuration_workbook
from .draft_generation import (
    DraftGenerationError,
    DraftProvider,
    DraftProviderDiagnosticError,
    FixtureDraftProvider,
    generate_docir_draft,
    generate_interface_standard_draft,
    generate_interface_template_draft,
    generate_schemair_draft,
    publish_generated_draft,
    publish_provider_failure,
)
from .openai_chat_provider import (
    DEFAULT_DOCIR_FIELD_BATCH_SIZE,
    OpenAIChatDraftProvider,
)
from .workspace import (
    Phase0Selection,
    WorkspaceError,
    check_workspace,
    ingest_raw_doc,
    load_phase0_artifacts,
    phase0_workbook_path,
    read_json_artifact,
    read_text_artifact,
)


LLM_ENVIRONMENT_NAMES = (
    "BANK_CONFIG_COMPILER_LLM_API_KEY",
    "BANK_CONFIG_COMPILER_LLM_BASE_URL",
    "BANK_CONFIG_COMPILER_LLM_MODEL",
    "BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS",
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

    draft = subparsers.add_parser(
        "generate-draft",
        help="Generate one provider-backed IR Draft without crossing the Human Review boundary.",
    )
    draft_kinds = draft.add_subparsers(dest="draft_kind", required=True)

    docir = draft_kinds.add_parser("docir", help="Generate docir-draft.md from raw-doc.md.")
    _add_draft_provider_arguments(docir)
    docir.add_argument(
        "--docir-field-batch-size",
        type=_positive_integer,
        help=(
            "Maximum fields per ASSEMBLY/PARSE detail subcall; "
            f"defaults to {DEFAULT_DOCIR_FIELD_BATCH_SIZE} for openai-chat."
        ),
    )

    schemair = draft_kinds.add_parser("schemair", help="Generate SchemaIR Draft from docir-final.md.")
    _add_draft_provider_arguments(schemair)

    standard = draft_kinds.add_parser(
        "standard",
        help="Generate one InterfaceStandardIR Draft from Final SchemaIR.",
    )
    _add_draft_provider_arguments(standard)
    _add_draft_direction(standard)
    standard.add_argument("--standard-version", required=True, help="Output Standard version.")
    standard.add_argument(
        "--rule-package",
        required=True,
        type=Path,
        help="Path to the Standard's RELEASED rule package.",
    )

    template = draft_kinds.add_parser(
        "template",
        help="Generate one InterfaceTemplateIR Draft from a reviewed Final Standard.",
    )
    _add_draft_provider_arguments(template)
    _add_draft_direction(template)
    template.add_argument("--standard-version", required=True, help="Bound Final Standard version.")
    template.add_argument("--template-id", required=True, help="Output Template stable ID.")
    template.add_argument("--template-version", required=True, help="Output Template version.")
    template.add_argument(
        "--rule-package",
        required=True,
        type=Path,
        help="Path to the Template's RELEASED rule package.",
    )

    return parser


def _add_draft_provider_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", required=True, type=Path, help="Workspace directory.")
    parser.add_argument(
        "--provider",
        required=True,
        choices=["fixture", "openai-chat"],
        help="Explicit Draft provider implementation.",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        help="Directory containing one explicit draft-stub-case.json.",
    )
    parser.add_argument(
        "--chat-base-url",
        help=(
            "OpenAI-compatible HTTPS base URL; overrides "
            "BANK_CONFIG_COMPILER_LLM_BASE_URL."
        ),
    )
    parser.add_argument(
        "--chat-model",
        help="Runtime-selected model ID; overrides BANK_CONFIG_COMPILER_LLM_MODEL.",
    )
    parser.add_argument(
        "--chat-timeout-seconds",
        type=float,
        help=(
            "Request timeout in seconds; overrides "
            "BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS and defaults to 600."
        ),
    )
    parser.add_argument(
        "--attempt-id",
        help="Auditable call attempt ID; required for the openai-chat provider.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Replace the existing Draft output set or DocIR provider failure evidence."
        ),
    )


def _add_draft_direction(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--direction",
        required=True,
        choices=["assembly", "parse"],
        help="Selected message direction.",
    )


def _positive_integer(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


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
        if args.command == "generate-draft":
            if args.provider == "openai-chat":
                args.llm_environment = _load_runtime_environment()
            output = _generate_draft(args)
            print(f"saved {args.draft_kind} Draft: {output}")
            return 0
    except (DraftGenerationError, WorkspaceError, RulePackageValidationError, WorkbookGenerationError) as exc:
        print(f"error: {_safe_error(exc)}", file=sys.stderr)
        return 2

    parser.error(f"unsupported command: {args.command}")
    return 2


def _generate_draft(args: argparse.Namespace) -> Path:
    workspace = args.workspace.resolve()
    provider = _draft_provider(args)
    task_id = workspace.name
    try:
        if args.draft_kind == "docir":
            generated = generate_docir_draft(
                raw_doc=read_text_artifact(workspace, "raw-doc.md"),
                provider=provider,
                task_id=task_id,
            )
        elif args.draft_kind == "schemair":
            generated = generate_schemair_draft(
                docir_final=read_text_artifact(workspace, "docir-final.md"),
                provider=provider,
                task_id=task_id,
            )
        elif args.draft_kind == "standard":
            generated = generate_interface_standard_draft(
                schemair_final=read_json_artifact(workspace, "schemair-final.json"),
                rule_package=load_rule_package(args.rule_package),
                direction=args.direction.upper(),
                standard_version=args.standard_version,
                provider=provider,
                task_id=task_id,
            )
        elif args.draft_kind == "template":
            standard_path = (
                f"standards/{args.direction}/{args.standard_version}/standard-final.json"
            )
            generated = generate_interface_template_draft(
                standard_final=read_json_artifact(workspace, standard_path),
                rule_package=load_rule_package(args.rule_package),
                direction=args.direction.upper(),
                standard_version=args.standard_version,
                template_id=args.template_id,
                template_version=args.template_version,
                provider=provider,
                task_id=task_id,
            )
        else:
            raise DraftGenerationError(f"unsupported Draft kind: {args.draft_kind}")
    except DraftProviderDiagnosticError as exc:
        # 失败证据属于显式 DocIR attempt 的开发诊断，不改变其他 IR 或 fixture 的输出协议。
        if (
            args.draft_kind == "docir"
            and args.provider == "openai-chat"
            and exc.evidence is not None
        ):
            publish_provider_failure(workspace, exc, overwrite=args.overwrite)
        raise
    outputs = publish_generated_draft(workspace, generated, overwrite=args.overwrite)
    return outputs["artifact"]


def _draft_provider(args: argparse.Namespace) -> DraftProvider:
    if args.provider == "fixture":
        if args.fixture_root is None:
            raise DraftGenerationError("fixture provider requires --fixture-root")
        if any(
            value is not None
            for value in (
                args.chat_base_url,
                args.chat_model,
                args.chat_timeout_seconds,
                args.attempt_id,
                getattr(args, "docir_field_batch_size", None),
            )
        ):
            raise DraftGenerationError(
                "fixture provider does not accept chat configuration"
            )
        return FixtureDraftProvider(args.fixture_root)

    if args.fixture_root is not None:
        raise DraftGenerationError("openai-chat provider does not accept --fixture-root")
    runtime_environment = getattr(args, "llm_environment", os.environ)
    base_url = (
        args.chat_base_url
        if args.chat_base_url is not None
        else runtime_environment.get("BANK_CONFIG_COMPILER_LLM_BASE_URL")
    )
    model = (
        args.chat_model
        if args.chat_model is not None
        else runtime_environment.get("BANK_CONFIG_COMPILER_LLM_MODEL")
    )
    required = {
        "--chat-base-url or BANK_CONFIG_COMPILER_LLM_BASE_URL": base_url,
        "--chat-model or BANK_CONFIG_COMPILER_LLM_MODEL": model,
        "--attempt-id": args.attempt_id,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise DraftGenerationError(
            f"openai-chat provider requires explicit arguments: {', '.join(missing)}"
        )
    api_key = runtime_environment.get("BANK_CONFIG_COMPILER_LLM_API_KEY")
    if not api_key:
        raise DraftGenerationError(
            "openai-chat provider requires BANK_CONFIG_COMPILER_LLM_API_KEY"
        )
    timeout_seconds = args.chat_timeout_seconds
    if timeout_seconds is None:
        timeout_value = runtime_environment.get("BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS")
        if timeout_value is None:
            timeout_seconds = 600.0
        else:
            try:
                timeout_seconds = float(timeout_value)
            except ValueError as exc:
                raise DraftGenerationError(
                    "BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS must be a number"
                ) from exc
    provider_arguments = {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "attempt_id": args.attempt_id,
        "timeout_seconds": timeout_seconds,
    }
    if getattr(args, "draft_kind", None) == "docir":
        provider_arguments["docir_field_batch_size"] = (
            getattr(args, "docir_field_batch_size", None)
            or DEFAULT_DOCIR_FIELD_BATCH_SIZE
        )
    return OpenAIChatDraftProvider(
        **provider_arguments,
    )


def _load_runtime_environment(dotenv_path: Path | None = None) -> dict[str, str]:
    path = dotenv_path if dotenv_path is not None else Path.cwd() / ".env"
    if not path.exists():
        return {
            name: value
            for name in LLM_ENVIRONMENT_NAMES
            if (value := os.environ.get(name)) is not None
        }
    if not path.is_file():
        raise DraftGenerationError(".env path must be a regular file")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DraftGenerationError(f"failed to read .env: {type(exc).__name__}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raise DraftGenerationError(".env must be UTF-8 without BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DraftGenerationError(".env must be valid UTF-8") from exc
    values = dotenv_values(stream=io.StringIO(text), interpolate=False)
    # 只加载 P0-T5 明确支持的配置，避免仓库内 dotenv 意外改变其他进程行为。
    runtime_environment: dict[str, str] = {}
    for name in LLM_ENVIRONMENT_NAMES:
        dotenv_value = values.get(name)
        if dotenv_value is not None:
            runtime_environment[name] = dotenv_value
        process_value = os.environ.get(name)
        if process_value is not None:
            runtime_environment[name] = process_value
    return runtime_environment


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
    failure_paths = getattr(exc, "failure_evidence_paths", ())
    if failure_paths:
        rendered_paths = ", ".join(str(path) for path in failure_paths)
        evidence = getattr(exc, "evidence", None)
        response_hash = getattr(evidence, "response_content_hash", None)
        hash_detail = f"; response hash: {response_hash}" if response_hash else ""
        return f"{exc}; failure evidence: {rendered_paths}{hash_detail}"
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
