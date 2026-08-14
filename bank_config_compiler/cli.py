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
    assert_provider_attempt_unused,
    generate_docir_draft,
    generate_interface_standard_draft,
    generate_interface_template_draft,
    generate_schemair_draft,
    publish_generated_draft,
    publish_provider_failure,
)
from .draft_review import (
    DraftReviewError,
    approve_draft,
    load_approved_docir_final,
    validate_current_draft,
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
    load_task_manifest,
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
    ingest.add_argument("--task-id", required=True, help="Lowercase kebab-case task identity.")
    ingest.add_argument("--interface-code", required=True, help="Explicit bank interface code.")
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
    schemair.add_argument("--schema-id", required=True, help="Locked SchemaIR stable ID.")
    schemair.add_argument("--schema-version", required=True, help="Locked SchemaIR version.")

    standard = draft_kinds.add_parser(
        "standard",
        help="Generate one InterfaceStandardIR Draft from Final SchemaIR.",
    )
    _add_draft_provider_arguments(standard)
    _add_draft_direction(standard)
    standard.add_argument("--standard-id", required=True, help="Locked Standard stable ID.")
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

    validate_draft = subparsers.add_parser(
        "validate-draft",
        help="Validate the current Human working Draft and replace its validation outputs.",
    )
    validate_draft.add_argument("kind", choices=["docir", "schemair", "standard", "template"])
    validate_draft.add_argument("--workspace", required=True, type=Path)
    _add_draft_review_arguments(validate_draft)

    approve = subparsers.add_parser(
        "approve-draft",
        help="Approve the exact validated Draft bytes and publish Final.",
    )
    approve.add_argument("kind", choices=["docir", "schemair", "standard", "template"])
    approve.add_argument("--workspace", required=True, type=Path)
    _add_draft_review_arguments(approve)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--review-note", required=True)
    approve.add_argument(
        "--expected-content-hash",
        help="Required for non-interactive approval; must match the exact current Draft bytes.",
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
            "Per-subcall absolute deadline in seconds; also configures SDK I/O "
            "timeouts, overrides BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS, and "
            "defaults to 600."
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
            "Replace the existing Draft output set; provider attempt evidence remains immutable."
        ),
    )


def _add_draft_direction(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--direction",
        required=True,
        choices=["assembly", "parse"],
        help="Selected message direction.",
    )


def _add_draft_review_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--direction", choices=["assembly", "parse"])
    parser.add_argument("--standard-version")
    parser.add_argument("--template-id")
    parser.add_argument("--template-version")
    parser.add_argument("--rule-package", type=Path)


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
            output_path = ingest_raw_doc(
                args.input,
                args.workspace,
                task_id=args.task_id,
                interface_code=args.interface_code,
                overwrite=args.overwrite,
            )
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
            command_result = _generate_draft(args)
            if isinstance(command_result, tuple):
                output, exit_code = command_result
            else:  # 兼容只替换 CLI 边界的既有测试 double；生产路径始终返回 tuple。
                output, exit_code = command_result, 0
            print(f"saved {args.draft_kind} Draft: {output}")
            return exit_code
        if args.command == "validate-draft":
            review_arguments = _draft_review_arguments(args)
            result = validate_current_draft(
                args.workspace, args.kind, **review_arguments
            )
            print(
                f"validated {args.kind} Draft: {result['status']} "
                f"({result['validatedArtifact']['contentHash']})"
            )
            return 3 if result["summary"]["errorCount"] else 0
        if args.command == "approve-draft":
            review_arguments = _draft_review_arguments(args)
            expected_hash = args.expected_content_hash
            if expected_hash is None:
                if not sys.stdin.isatty():
                    raise DraftReviewError(
                        "non-interactive approval requires --expected-content-hash"
                    )
                validation = validate_current_draft(
                    args.workspace, args.kind, **review_arguments
                )
                expected_hash = validation["validatedArtifact"]["contentHash"]
                _print_interactive_approval_summary(args, validation)
                print(f"Reviewer: {args.reviewer}")
                print(f"Review note: {args.review_note}")
                print(f"Content hash: {expected_hash}")
                confirmation = input("Approve these exact Draft bytes? [y/N]: ").strip().lower()
                if confirmation not in {"y", "yes"}:
                    raise DraftReviewError("approval was not confirmed")
            approval = approve_draft(
                args.workspace,
                args.kind,
                reviewer=args.reviewer,
                review_note=args.review_note,
                expected_content_hash=expected_hash,
                **review_arguments,
            )
            print(
                f"approved {args.kind} Draft: {approval['finalArtifact']} "
                f"({approval['finalHash']})"
            )
            return 0
    except (
        DraftGenerationError,
        DraftReviewError,
        WorkspaceError,
        RulePackageValidationError,
        WorkbookGenerationError,
    ) as exc:
        print(f"error: {_safe_error(exc)}", file=sys.stderr)
        return 2

    parser.error(f"unsupported command: {args.command}")
    return 2


def _generate_draft(args: argparse.Namespace) -> tuple[Path, int]:
    workspace = args.workspace.resolve()
    task = load_task_manifest(workspace)
    approved_docir_final = None
    if args.draft_kind == "schemair":
        # approval result 是可信链提交标记；先校验，再构造任何可能访问外部 provider 的对象。
        approved_docir_final = load_approved_docir_final(workspace, task=task)
    provider = _draft_provider(args)
    if args.provider == "openai-chat":
        assert_provider_attempt_unused(
            workspace, getattr(provider, "attempt_id", None)
        )
    task_id = task["taskId"]
    try:
        if args.draft_kind == "docir":
            generated = generate_docir_draft(
                raw_doc=read_text_artifact(workspace, "raw-doc.md"),
                provider=provider,
                task_id=task_id,
                interface_code=task["interfaceCode"],
            )
        elif args.draft_kind == "schemair":
            generated = generate_schemair_draft(
                docir_final=approved_docir_final,
                provider=provider,
                task_id=task_id,
                interface_code=task["interfaceCode"],
                schema_id=args.schema_id,
                schema_version=args.schema_version,
            )
        elif args.draft_kind == "standard":
            generated = generate_interface_standard_draft(
                schemair_final=read_json_artifact(workspace, "schemair-final.json"),
                rule_package=load_rule_package(args.rule_package),
                direction=args.direction.upper(),
                standard_id=args.standard_id,
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
        # 失败 attempt 也必须消费 ID；否则重跑可能覆盖或混淆外部调用证据。
        if (
            args.provider == "openai-chat"
            and exc.evidence is not None
        ):
            publish_provider_failure(workspace, exc, overwrite=args.overwrite)
        raise
    outputs = publish_generated_draft(workspace, generated, overwrite=args.overwrite)
    return outputs["artifact"], 3 if generated.publication_state == "invalid" else 0


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


def _draft_review_arguments(args: argparse.Namespace) -> dict[str, object]:
    supplied = {
        "direction": args.direction.upper() if args.direction else None,
        "standard_version": args.standard_version,
        "template_id": args.template_id,
        "template_version": args.template_version,
        "rule_package": (
            load_rule_package(args.rule_package) if args.rule_package is not None else None
        ),
    }
    if args.kind in {"docir", "schemair"}:
        if any(value is not None for value in supplied.values()):
            raise DraftReviewError(
                f"{args.kind} review does not accept direction, version or rule package selectors"
            )
        return supplied
    required = {
        "--direction": supplied["direction"],
        "--standard-version": supplied["standard_version"],
        "--rule-package": supplied["rule_package"],
    }
    if args.kind == "template":
        required.update(
            {
                "--template-id": supplied["template_id"],
                "--template-version": supplied["template_version"],
            }
        )
    elif supplied["template_id"] is not None or supplied["template_version"] is not None:
        raise DraftReviewError("standard review does not accept template selectors")
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise DraftReviewError(
            f"{args.kind} review requires explicit arguments: {', '.join(missing)}"
        )
    return supplied


def _print_interactive_approval_summary(
    args: argparse.Namespace, validation: dict[str, object]
) -> None:
    task = load_task_manifest(args.workspace)
    validated = validation["validatedArtifact"]
    summary = validation["summary"]
    if not isinstance(validated, dict) or not isinstance(summary, dict):
        raise DraftReviewError("validation result cannot be summarized for approval")
    identity = [
        f"taskId={task['taskId']}",
        f"interfaceCode={task['interfaceCode']}",
        f"kind={args.kind}",
    ]
    for key in ("artifactId", "artifactVersion", "artifactContractVersion"):
        value = validated.get(key)
        if value is not None:
            identity.append(f"{key}={value}")
    for key in ("direction", "standard_version", "template_id", "template_version"):
        value = getattr(args, key, None)
        if value is not None:
            identity.append(f"{key}={value}")
    print("Artifact identity: " + ", ".join(identity))
    print(
        "Validation summary: "
        f"ERROR={summary.get('errorCount')}, "
        f"WARNING={summary.get('warningCount')}, "
        f"INFO={summary.get('infoCount')}"
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
