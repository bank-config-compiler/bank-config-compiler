from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from .artifact_validation import canonical_json_bytes, content_hash
from .configuration_rules import RulePackage
from .interface_standard_validator import validate_interface_standard
from .interface_template_validator import validate_interface_template
from .schemair_validator import validate_schemair
from .workspace import artifact_path, ensure_workspace_dir


LOGGER = logging.getLogger(__name__)

PROVIDER_RESPONSE_CONTRACT = "draft-provider-response/v1"
PROVIDER_CALL_RESULT_CONTRACT = "draft-provider-call-result/v1"
PROVIDER_FAILURE_RESULT_CONTRACT = "draft-provider-failure-result/v1"
STUB_CASE_CONTRACT = "draft-stub-case/v1"
ARTIFACT_KINDS = {"docir", "schemair", "standard", "template"}
DIRECTIONS = {"ASSEMBLY", "PARSE"}
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
VERSION_PATTERN = re.compile(r"^v[1-9]\d*$")
STABLE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESPONSE_PROPERTIES = {"contractVersion", "artifactKind", "artifactContent", "reviewNotes"}
CASE_PROPERTIES = {"contractVersion", "caseId", "responses"}
CASE_ENTRY_PROPERTIES = {"request", "artifactFile", "reviewNotesFile"}
CASE_REQUEST_PROPERTIES = {
    "artifactKind",
    "sourceHash",
    "direction",
    "standardVersion",
    "templateId",
    "templateVersion",
    "rulePackageVersion",
}

ArtifactKind = Literal["docir", "schemair", "standard", "template"]
ProviderFailureStage = Literal[
    "request",
    "stream",
    "model-response",
    "docir-extraction",
    "provider-response",
]


class DraftGenerationError(Exception):
    """Raised when a provider or generated Draft fails the P0 trust boundary."""


class DraftProviderDiagnosticError(DraftGenerationError):
    """开发期 provider 门禁诊断；detail 可由 CLI 直接展示。"""

    def __init__(
        self,
        message: str,
        *,
        evidence: ProviderFailureEvidence | None = None,
    ) -> None:
        super().__init__(message)
        self.evidence = evidence
        self.failure_evidence_paths: tuple[Path, ...] = ()

    def bind_failure_evidence_paths(self, paths: tuple[Path, ...]) -> None:
        self.failure_evidence_paths = paths


class _FixtureProviderError(DraftGenerationError):
    """仅标记受控 fixture 的可诊断错误；其他 provider 异常必须统一脱敏。"""


class DraftProvider(Protocol):
    name: str

    def generate(
        self,
        request: DraftGenerationRequest,
        context: DraftGenerationContext,
    ) -> DraftProviderResult:
        """Return one response envelope and non-sensitive call metadata."""


@dataclass(frozen=True, slots=True)
class DraftGenerationRequest:
    task_id: str
    artifact_kind: ArtifactKind
    source_hash: str
    direction: str | None = None
    standard_version: str | None = None
    template_id: str | None = None
    template_version: str | None = None
    rule_package_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise DraftGenerationError("task_id must be a non-empty string")
        if self.artifact_kind not in ARTIFACT_KINDS:
            raise DraftGenerationError(f"unsupported artifact kind: {self.artifact_kind}")
        if not isinstance(self.source_hash, str) or not SHA256_PATTERN.fullmatch(
            self.source_hash
        ):
            raise DraftGenerationError("source_hash must use sha256:<64 lowercase hex>")
        if self.direction is not None and self.direction not in DIRECTIONS:
            raise DraftGenerationError("direction must be exactly ASSEMBLY or PARSE")
        if self.standard_version is not None and not VERSION_PATTERN.fullmatch(
            self.standard_version
        ):
            raise DraftGenerationError("standard_version must match v<positive integer>")
        if self.template_id is not None and not STABLE_ID_PATTERN.fullmatch(self.template_id):
            raise DraftGenerationError("template_id must be a kebab-case stable ID")
        if self.template_version is not None and not VERSION_PATTERN.fullmatch(self.template_version):
            raise DraftGenerationError("template_version must match v<positive integer>")
        if self.rule_package_version is not None and not VERSION_PATTERN.fullmatch(
            self.rule_package_version
        ):
            raise DraftGenerationError("rule_package_version must match v<positive integer>")
        self._validate_selectors()

    def _validate_selectors(self) -> None:
        if self.artifact_kind in {"docir", "schemair"}:
            if any(
                value is not None
                for value in (
                    self.direction,
                    self.standard_version,
                    self.template_id,
                    self.template_version,
                    self.rule_package_version,
                )
            ):
                raise DraftGenerationError(f"{self.artifact_kind} request does not accept selectors")
            return
        if self.artifact_kind == "standard":
            if (
                self.direction is None
                or self.standard_version is None
                or self.rule_package_version is None
            ):
                raise DraftGenerationError(
                    "standard request requires direction, standard_version and rule_package_version"
                )
            if self.template_id is not None or self.template_version is not None:
                raise DraftGenerationError("standard request does not accept template selectors")
            return
        if any(
            value is None
            for value in (
                self.direction,
                self.standard_version,
                self.template_id,
                self.template_version,
                self.rule_package_version,
            )
        ):
            raise DraftGenerationError(
                "template request requires direction, standard_version, template_id, "
                "template_version and rule_package_version"
            )

    def case_fingerprint(self) -> dict[str, str]:
        values = {
            "artifactKind": self.artifact_kind,
            "sourceHash": self.source_hash,
            "direction": self.direction,
            "standardVersion": self.standard_version,
            "templateId": self.template_id,
            "templateVersion": self.template_version,
            "rulePackageVersion": self.rule_package_version,
        }
        return {key: value for key, value in values.items() if value is not None}


@dataclass(frozen=True, slots=True)
class DraftGenerationContext:
    source_content: str
    source_content_type: Literal["text/markdown", "application/json"]
    rule_package_content: str | None = None
    rule_package_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_content, str) or not self.source_content.strip():
            raise DraftGenerationError("source_content must be a non-empty string")
        if self.source_content.startswith("\ufeff"):
            raise DraftGenerationError("source_content must be UTF-8 without BOM")
        if self.source_content_type not in {"text/markdown", "application/json"}:
            raise DraftGenerationError("unsupported source_content_type")
        if (self.rule_package_content is None) != (self.rule_package_version is None):
            raise DraftGenerationError(
                "rule_package_content and rule_package_version must be provided together"
            )
        if self.rule_package_content is not None:
            _strict_json_object(self.rule_package_content, label="rule package context")
            if not VERSION_PATTERN.fullmatch(self.rule_package_version or ""):
                raise DraftGenerationError("rule_package_version must match v<positive integer>")

    def source_hash(self) -> str:
        if self.source_content_type == "text/markdown":
            return _text_hash(self.source_content)
        return content_hash(_strict_json_object(self.source_content, label="source context"))


@dataclass(frozen=True, slots=True)
class ProviderCallMetadata:
    provider_name: str
    attempt_id: str | None = None
    requested_model: str | None = None
    response_model: str | None = None
    response_id: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    endpoint_fingerprint: str | None = None
    prompt_contract_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider_name, str) or not self.provider_name.strip():
            raise DraftGenerationError("provider metadata name must be a non-empty string")
        for label, value in (
            ("attempt_id", self.attempt_id),
            ("requested_model", self.requested_model),
            ("response_model", self.response_model),
            ("response_id", self.response_id),
            ("started_at", self.started_at),
            ("completed_at", self.completed_at),
            ("prompt_contract_version", self.prompt_contract_version),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise DraftGenerationError(f"provider metadata {label} must be non-empty")
        for label, value in (
            ("prompt_tokens", self.prompt_tokens),
            ("completion_tokens", self.completion_tokens),
            ("total_tokens", self.total_tokens),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise DraftGenerationError(
                    f"provider metadata {label} must be a non-negative integer"
                )
        if self.endpoint_fingerprint is not None and not SHA256_PATTERN.fullmatch(
            self.endpoint_fingerprint
        ):
            raise DraftGenerationError("provider endpoint fingerprint must be a SHA-256 hash")


@dataclass(frozen=True, slots=True)
class ProviderFailureEvidence:
    """可由编排层持久化的失败调用事实，不携带 workspace 或 credential。"""

    request: DraftGenerationRequest
    metadata: ProviderCallMetadata
    failure_stage: ProviderFailureStage
    failure_detail: str
    error_type: str | None
    response_complete: bool
    response_text: str | None
    finish_reason: str | None

    @property
    def response_content_hash(self) -> str | None:
        if self.response_text is None:
            return None
        return _text_hash(self.response_text)

    def __post_init__(self) -> None:
        if self.failure_stage not in {
            "request",
            "stream",
            "model-response",
            "docir-extraction",
            "provider-response",
        }:
            raise DraftGenerationError("provider failure stage is invalid")
        if not isinstance(self.failure_detail, str) or not self.failure_detail.strip():
            raise DraftGenerationError("provider failure detail must be non-empty")
        if self.error_type is not None and (
            not isinstance(self.error_type, str) or not self.error_type.strip()
        ):
            raise DraftGenerationError("provider failure error type must be non-empty")
        if not isinstance(self.response_complete, bool):
            raise DraftGenerationError("provider responseComplete must be boolean")
        if self.response_text is not None and (
            not isinstance(self.response_text, str) or not self.response_text
        ):
            raise DraftGenerationError("provider failure response text must be non-empty")
        if self.finish_reason is not None and (
            not isinstance(self.finish_reason, str) or not self.finish_reason.strip()
        ):
            raise DraftGenerationError("provider finish reason must be non-empty")


@dataclass(frozen=True, slots=True)
class DraftProviderResult:
    response_text: str
    metadata: ProviderCallMetadata


@dataclass(frozen=True, slots=True)
class GeneratedDraft:
    request: DraftGenerationRequest
    provider_name: str
    artifact: str | dict[str, Any]
    review_notes: str
    validation_result: dict[str, Any] | None
    content_hash: str
    provider_metadata: ProviderCallMetadata


class FixtureDraftProvider:
    """Load deterministic responses from one explicitly selected P0 stub case."""

    name = "fixture"

    def __init__(self, fixture_root: Path) -> None:
        self.fixture_root = fixture_root.resolve()
        if not self.fixture_root.is_dir():
            raise DraftGenerationError(f"fixture root is not a directory: {self.fixture_root}")
        manifest_path = self.fixture_root / "draft-stub-case.json"
        manifest = _strict_json_object(_read_utf8_text(manifest_path), label="draft-stub-case.json")
        _require_exact_properties(manifest, CASE_PROPERTIES, label="draft-stub-case.json")
        if manifest.get("contractVersion") != STUB_CASE_CONTRACT:
            raise DraftGenerationError(f"fixture case contractVersion must be {STUB_CASE_CONTRACT}")
        case_id = manifest.get("caseId")
        if not isinstance(case_id, str) or not STABLE_ID_PATTERN.fullmatch(case_id):
            raise DraftGenerationError("fixture caseId must be a kebab-case stable ID")
        responses = manifest.get("responses")
        if not isinstance(responses, list) or not responses:
            raise DraftGenerationError("fixture responses must be a non-empty array")
        self.case_id = case_id
        self._responses = self._validate_responses(responses)

    def _validate_responses(self, responses: list[Any]) -> dict[str, tuple[Path, Path]]:
        indexed: dict[str, tuple[Path, Path]] = {}
        for index, entry in enumerate(responses):
            label = f"responses[{index}]"
            if not isinstance(entry, dict):
                raise DraftGenerationError(f"{label} must be an object")
            _require_exact_properties(entry, CASE_ENTRY_PROPERTIES, label=label)
            request = _request_from_case(entry.get("request"), label=f"{label}.request")
            key = _fingerprint_key(request.case_fingerprint())
            if key in indexed:
                raise DraftGenerationError(f"duplicate fixture request: {key}")
            artifact_path = self._case_file(entry.get("artifactFile"), label=f"{label}.artifactFile")
            notes_path = self._case_file(entry.get("reviewNotesFile"), label=f"{label}.reviewNotesFile")
            indexed[key] = (artifact_path, notes_path)
        return indexed

    def _case_file(self, value: Any, *, label: str) -> Path:
        if not isinstance(value, str) or not value:
            raise DraftGenerationError(f"{label} must be a non-empty relative path")
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise DraftGenerationError(f"{label} must stay within the fixture root")
        resolved = (self.fixture_root / relative).resolve()
        try:
            resolved.relative_to(self.fixture_root)
        except ValueError as exc:
            raise DraftGenerationError(f"{label} must stay within the fixture root") from exc
        if not resolved.is_file():
            raise DraftGenerationError(f"{label} does not exist: {value}")
        return resolved

    def generate(
        self,
        request: DraftGenerationRequest,
        context: DraftGenerationContext,
    ) -> DraftProviderResult:
        key = _fingerprint_key(request.case_fingerprint())
        files = self._responses.get(key)
        if files is None:
            raise _FixtureProviderError(
                f"fixture case {self.case_id} has no exact response for request {key}"
            )
        try:
            artifact_content = _read_utf8_text(files[0])
            review_notes = _read_utf8_text(files[1])
        except DraftGenerationError as exc:
            raise _FixtureProviderError(str(exc)) from exc
        return DraftProviderResult(
            response_text=json.dumps(
                {
                    "contractVersion": PROVIDER_RESPONSE_CONTRACT,
                    "artifactKind": request.artifact_kind,
                    "artifactContent": artifact_content,
                    "reviewNotes": review_notes,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            metadata=ProviderCallMetadata(provider_name=self.name),
        )


def generate_docir_draft(*, raw_doc: str, provider: DraftProvider, task_id: str) -> GeneratedDraft:
    request = DraftGenerationRequest(
        task_id=task_id,
        artifact_kind="docir",
        source_hash=_text_hash(raw_doc),
    )
    artifact_content, review_notes, metadata = _provider_content(
        provider,
        request,
        _text_context(raw_doc),
    )
    _validate_docir_structure(artifact_content)
    draft_hash = _text_hash(artifact_content)
    return _generated(
        request=request,
        provider=provider,
        artifact=artifact_content,
        review_notes=review_notes,
        validation_result=None,
        draft_hash=draft_hash,
        provider_metadata=metadata,
    )


def generate_schemair_draft(
    *,
    docir_final: str,
    provider: DraftProvider,
    task_id: str,
) -> GeneratedDraft:
    request = DraftGenerationRequest(
        task_id=task_id,
        artifact_kind="schemair",
        source_hash=_text_hash(docir_final),
    )
    artifact_content, review_notes, metadata = _provider_content(
        provider,
        request,
        _text_context(docir_final),
    )
    artifact = _strict_json_object(artifact_content, label="SchemaIR Draft")
    _require_pending_draft(artifact, label="SchemaIR")
    result = validate_schemair(artifact)
    _require_valid_draft_result(result, label="SchemaIR")
    return _generated_json(request, provider, artifact, review_notes, result, metadata)


def generate_interface_standard_draft(
    *,
    schemair_final: dict[str, Any],
    rule_package: RulePackage,
    direction: str,
    standard_version: str,
    provider: DraftProvider,
    task_id: str,
) -> GeneratedDraft:
    _require_released_rule_package(rule_package)
    schema_result = validate_schemair(schemair_final)
    if not schema_result.get("finalEligible"):
        raise DraftGenerationError("Standard generator requires a reviewed Final SchemaIR")
    request = DraftGenerationRequest(
        task_id=task_id,
        artifact_kind="standard",
        source_hash=content_hash(schemair_final),
        direction=direction,
        standard_version=standard_version,
        rule_package_version=rule_package.version,
    )
    artifact_content, review_notes, metadata = _provider_content(
        provider,
        request,
        _json_context(schemair_final, rule_package),
    )
    artifact = _strict_json_object(artifact_content, label="InterfaceStandardIR Draft")
    _require_pending_draft(artifact, label="InterfaceStandardIR")
    _require_matching_request_identity(
        artifact,
        expected={
            "direction": request.direction,
            "standardVersion": request.standard_version,
        },
        label="InterfaceStandardIR",
    )
    result = validate_interface_standard(
        artifact,
        schemair=schemair_final,
        rule_package=rule_package,
    )
    _require_valid_draft_result(result, label="InterfaceStandardIR")
    return _generated_json(request, provider, artifact, review_notes, result, metadata)


def generate_interface_template_draft(
    *,
    standard_final: dict[str, Any],
    rule_package: RulePackage,
    direction: str,
    standard_version: str,
    template_id: str,
    template_version: str,
    provider: DraftProvider,
    task_id: str,
) -> GeneratedDraft:
    _require_released_rule_package(rule_package)
    review = standard_final.get("review") if isinstance(standard_final, dict) else None
    if (
        not isinstance(standard_final, dict)
        or standard_final.get("status") != "FINAL"
        or not isinstance(review, dict)
        or review.get("status") != "APPROVED"
    ):
        raise DraftGenerationError("Template generator requires a reviewed Final InterfaceStandardIR")
    if standard_final.get("direction") != direction:
        raise DraftGenerationError("Template direction must match the Final InterfaceStandardIR")
    if standard_final.get("standardVersion") != standard_version:
        raise DraftGenerationError("Template standard_version must match the Final InterfaceStandardIR")
    request = DraftGenerationRequest(
        task_id=task_id,
        artifact_kind="template",
        source_hash=content_hash(standard_final),
        direction=direction,
        standard_version=standard_version,
        template_id=template_id,
        template_version=template_version,
        rule_package_version=rule_package.version,
    )
    artifact_content, review_notes, metadata = _provider_content(
        provider,
        request,
        _json_context(standard_final, rule_package),
    )
    artifact = _strict_json_object(artifact_content, label="InterfaceTemplateIR Draft")
    _require_pending_draft(artifact, label="InterfaceTemplateIR")
    _require_matching_request_identity(
        artifact,
        expected={
            "direction": request.direction,
            "templateId": request.template_id,
            "templateVersion": request.template_version,
        },
        label="InterfaceTemplateIR",
    )
    result = validate_interface_template(artifact, standard=standard_final, rule_package=rule_package)
    _require_valid_draft_result(result, label="InterfaceTemplateIR")
    return _generated_json(request, provider, artifact, review_notes, result, metadata)


def publish_generated_draft(
    workspace_path: Path,
    generated: GeneratedDraft,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Publish one fully validated Draft output set without exposing temporary files."""

    ensure_workspace_dir(workspace_path)
    include_provider_call = generated.provider_metadata.attempt_id is not None
    names = _draft_artifact_names(
        generated.request,
        include_provider_call=include_provider_call,
    )
    outputs = {key: artifact_path(workspace_path, name) for key, name in names.items()}
    payloads: dict[str, bytes] = {
        "artifact": _serialize_artifact(generated.artifact),
        "review_notes": generated.review_notes.encode("utf-8"),
    }
    if generated.validation_result is not None:
        payloads["validation_result"] = _serialize_json(generated.validation_result)
    if include_provider_call:
        payloads["provider_call_result"] = _serialize_json(
            _provider_call_result(generated)
        )
    if set(outputs) != set(payloads):
        raise DraftGenerationError("generated Draft output set is internally inconsistent")

    _atomic_publish_payloads(
        outputs,
        payloads,
        overwrite=overwrite,
        existing_label="Draft output",
        failure_label="Draft outputs",
    )
    return outputs


def publish_provider_failure(
    workspace_path: Path,
    error: DraftProviderDiagnosticError,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Persist DocIR diagnostic evidence without turning it into a Draft artifact."""

    evidence = error.evidence
    if evidence is None:
        raise DraftGenerationError("provider failure does not contain diagnostic evidence")
    if evidence.request.artifact_kind != "docir":
        raise DraftGenerationError("only DocIR provider failure evidence is supported")
    ensure_workspace_dir(workspace_path)
    outputs = {
        "failure_result": artifact_path(
            workspace_path, "docir-provider-failure-result.json"
        )
    }
    response_path = artifact_path(
        workspace_path, "docir-provider-failure-response.txt"
    )
    payloads = {
        "failure_result": _serialize_json(_provider_failure_result(evidence))
    }
    if evidence.response_text is not None:
        outputs["failure_response"] = response_path
        payloads["failure_response"] = evidence.response_text.encode("utf-8")
    _atomic_publish_payloads(
        outputs,
        payloads,
        overwrite=overwrite,
        existing_label="provider failure evidence",
        failure_label="provider failure evidence",
    )
    if evidence.response_text is None and overwrite and response_path.exists():
        # 新摘要明确表示没有响应内容，不能让上一次 attempt 的响应文件伪装成当前证据。
        try:
            response_path.unlink()
        except OSError as exc:
            raise DraftGenerationError(
                "failed to remove stale provider failure response: "
                f"{type(exc).__name__}"
            ) from exc
    paths = tuple(outputs.values())
    error.bind_failure_evidence_paths(paths)
    LOGGER.warning(
        "Saved IR Draft provider failure evidence",
        extra={
            "component": "draft_generation",
            "task_id": evidence.request.task_id,
            "provider": evidence.metadata.provider_name,
            "artifact_kind": evidence.request.artifact_kind,
            "attempt_id": evidence.metadata.attempt_id,
            "requested_model": evidence.metadata.requested_model,
            "failure_stage": evidence.failure_stage,
            "response_complete": evidence.response_complete,
            "response_content_hash": (
                _text_hash(evidence.response_text)
                if evidence.response_text is not None
                else None
            ),
            "evidence_paths": [str(path) for path in paths],
            "outcome": "saved",
        },
    )
    return outputs


def _atomic_publish_payloads(
    outputs: dict[str, Path],
    payloads: dict[str, bytes],
    *,
    overwrite: bool,
    existing_label: str,
    failure_label: str,
) -> None:
    if set(outputs) != set(payloads):
        raise DraftGenerationError("output set is internally inconsistent")
    existing = [path for path in outputs.values() if path.exists()]
    if existing and not overwrite:
        rendered = ", ".join(path.name for path in existing)
        raise DraftGenerationError(
            f"{existing_label} already exists: {rendered}; pass --overwrite to replace it"
        )

    staged: dict[str, Path] = {}
    try:
        for key, output_path in outputs.items():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
            )
            temporary_path = Path(temporary_name)
            staged[key] = temporary_path
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payloads[key])
                handle.flush()
                os.fsync(handle.fileno())
        # 普通文件系统不能跨多个文件提交事务；逐文件原子替换后由 result/hash 让中断状态保持 fail closed。
        for key, output_path in outputs.items():
            temporary_path = staged[key]
            os.replace(temporary_path, output_path)
            staged.pop(key)
    except (OSError, ValueError, TypeError) as exc:
        for temporary_path in staged.values():
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise DraftGenerationError(
            f"failed to publish {failure_label}: {type(exc).__name__}"
        ) from exc


def _draft_artifact_names(
    request: DraftGenerationRequest,
    *,
    include_provider_call: bool = False,
) -> dict[str, str]:
    if request.artifact_kind == "docir":
        names = {
            "artifact": "docir-draft.md",
            "review_notes": "docir-review-notes.md",
        }
        if include_provider_call:
            names["provider_call_result"] = "docir-provider-call-result.json"
        return names
    if request.artifact_kind == "schemair":
        names = {
            "artifact": "schemair-draft.json",
            "review_notes": "schemair-review-notes.md",
            "validation_result": "schemair-validation-result.json",
        }
        if include_provider_call:
            names["provider_call_result"] = "schemair-provider-call-result.json"
        return names
    direction = request.direction.lower() if request.direction else ""
    if request.artifact_kind == "standard":
        root = f"standards/{direction}/{request.standard_version}"
        names = {
            "artifact": f"{root}/standard-draft.json",
            "review_notes": f"{root}/standard-review-notes.md",
            "validation_result": f"{root}/standard-validation-result.json",
        }
        if include_provider_call:
            names["provider_call_result"] = f"{root}/standard-provider-call-result.json"
        return names
    root = f"templates/{direction}/{request.template_id}/{request.template_version}"
    names = {
        "artifact": f"{root}/template-draft.json",
        "review_notes": f"{root}/template-review-notes.md",
        "validation_result": f"{root}/template-validation-result.json",
    }
    if include_provider_call:
        names["provider_call_result"] = f"{root}/template-provider-call-result.json"
    return names


def _provider_call_result(generated: GeneratedDraft) -> dict[str, Any]:
    metadata = generated.provider_metadata
    required = {
        "attemptId": metadata.attempt_id,
        "requestedModel": metadata.requested_model,
        "startedAt": metadata.started_at,
        "completedAt": metadata.completed_at,
        "endpointFingerprint": metadata.endpoint_fingerprint,
        "promptContractVersion": metadata.prompt_contract_version,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise DraftGenerationError(
            "auditable provider metadata is incomplete: " + ", ".join(missing)
        )
    selector = generated.request.case_fingerprint()
    selector.pop("artifactKind")
    selector.pop("sourceHash")
    return {
        "contractVersion": PROVIDER_CALL_RESULT_CONTRACT,
        "taskId": generated.request.task_id,
        "artifactKind": generated.request.artifact_kind,
        "sourceHash": generated.request.source_hash,
        "selectors": selector,
        "provider": metadata.provider_name,
        "attemptId": metadata.attempt_id,
        "requestedModel": metadata.requested_model,
        "responseModel": metadata.response_model,
        "responseId": metadata.response_id,
        "promptContractVersion": metadata.prompt_contract_version,
        "endpointFingerprint": metadata.endpoint_fingerprint,
        "startedAt": metadata.started_at,
        "completedAt": metadata.completed_at,
        "usage": {
            "promptTokens": metadata.prompt_tokens,
            "completionTokens": metadata.completion_tokens,
            "totalTokens": metadata.total_tokens,
        },
        "artifactContentHash": generated.content_hash,
    }


def _provider_failure_result(evidence: ProviderFailureEvidence) -> dict[str, Any]:
    metadata = evidence.metadata
    return {
        "contractVersion": PROVIDER_FAILURE_RESULT_CONTRACT,
        "taskId": evidence.request.task_id,
        "artifactKind": evidence.request.artifact_kind,
        "sourceHash": evidence.request.source_hash,
        "provider": metadata.provider_name,
        "attemptId": metadata.attempt_id,
        "requestedModel": metadata.requested_model,
        "responseModel": metadata.response_model,
        "responseId": metadata.response_id,
        "promptContractVersion": metadata.prompt_contract_version,
        "endpointFingerprint": metadata.endpoint_fingerprint,
        "startedAt": metadata.started_at,
        "completedAt": metadata.completed_at,
        "failureStage": evidence.failure_stage,
        "failureDetail": evidence.failure_detail,
        "errorType": evidence.error_type,
        "finishReason": evidence.finish_reason,
        "responseComplete": evidence.response_complete,
        "responseContentHash": (
            _text_hash(evidence.response_text)
            if evidence.response_text is not None
            else None
        ),
        "usage": {
            "promptTokens": metadata.prompt_tokens,
            "completionTokens": metadata.completion_tokens,
            "totalTokens": metadata.total_tokens,
        },
    }


def _serialize_artifact(artifact: str | dict[str, Any]) -> bytes:
    if isinstance(artifact, str):
        return artifact.encode("utf-8")
    return _serialize_json(artifact)


def _serialize_json(value: dict[str, Any]) -> bytes:
    try:
        return (
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DraftGenerationError("Draft output must contain only finite JSON values") from exc


def _provider_content(
    provider: DraftProvider,
    request: DraftGenerationRequest,
    context: DraftGenerationContext,
) -> tuple[str, str, ProviderCallMetadata]:
    provider_name = getattr(provider, "name", None)
    if not isinstance(provider_name, str) or not provider_name:
        raise DraftGenerationError("provider must expose a non-empty name")
    LOGGER.info(
        "Generating IR Draft",
        extra={
            "component": "draft_generation",
            "task_id": request.task_id,
            "provider": provider_name,
            "artifact_kind": request.artifact_kind,
            "direction": request.direction,
            "attempt_id": getattr(provider, "attempt_id", None),
            "requested_model": getattr(provider, "model", None),
            "outcome": "started",
        },
    )
    if context.source_hash() != request.source_hash:
        raise DraftGenerationError("provider context source hash does not match the request")
    if context.rule_package_version != request.rule_package_version:
        raise DraftGenerationError("provider context rule package does not match the request")
    try:
        provider_result = provider.generate(request, context)
    except _FixtureProviderError:
        LOGGER.warning(
            "IR Draft generation failed",
            extra={
                "component": "draft_generation",
                "task_id": request.task_id,
                "provider": provider_name,
                "artifact_kind": request.artifact_kind,
                "direction": request.direction,
                "attempt_id": getattr(provider, "attempt_id", None),
                "requested_model": getattr(provider, "model", None),
                "outcome": "failed",
            },
        )
        raise
    except DraftProviderDiagnosticError as exc:
        LOGGER.warning(
            "IR Draft provider validation failed",
            extra={
                "component": "draft_generation",
                "task_id": request.task_id,
                "provider": provider_name,
                "artifact_kind": request.artifact_kind,
                "direction": request.direction,
                "attempt_id": getattr(provider, "attempt_id", None),
                "requested_model": getattr(provider, "model", None),
                "outcome": "failed",
                "failure_detail": str(exc),
            },
        )
        raise
    except Exception as exc:
        LOGGER.warning(
            "IR Draft provider failed",
            extra={
                "component": "draft_generation",
                "task_id": request.task_id,
                "provider": provider_name,
                "artifact_kind": request.artifact_kind,
                "direction": request.direction,
                "attempt_id": getattr(provider, "attempt_id", None),
                "requested_model": getattr(provider, "model", None),
                "outcome": "failed",
                "error_type": type(exc).__name__,
            },
        )
        raise DraftGenerationError(f"provider {provider_name} failed: {type(exc).__name__}") from exc

    if not isinstance(provider_result, DraftProviderResult):
        raise DraftGenerationError("provider must return DraftProviderResult")
    if provider_result.metadata.provider_name != provider_name:
        raise DraftGenerationError("provider metadata name does not match the provider")
    try:
        response = _strict_json_object(provider_result.response_text, label="provider response")
        _require_exact_properties(response, RESPONSE_PROPERTIES, label="provider response")
        if response.get("contractVersion") != PROVIDER_RESPONSE_CONTRACT:
            raise DraftGenerationError(
                f"provider response contractVersion must be {PROVIDER_RESPONSE_CONTRACT}"
            )
        if response.get("artifactKind") != request.artifact_kind:
            raise DraftGenerationError("provider response artifactKind does not match the request")
        artifact_content = response.get("artifactContent")
        review_notes = response.get("reviewNotes")
        if not isinstance(artifact_content, str) or not artifact_content.strip():
            raise DraftGenerationError("provider response artifactContent must be a non-empty string")
        if artifact_content.startswith("\ufeff"):
            raise DraftGenerationError("provider response artifactContent must be UTF-8 without BOM")
        if not isinstance(review_notes, str) or not review_notes.strip():
            raise DraftGenerationError("provider response reviewNotes must be a non-empty string")
    except DraftGenerationError:
        LOGGER.warning(
            "IR Draft generation failed",
            extra={
                "component": "draft_generation",
                "task_id": request.task_id,
                "provider": provider_name,
                "artifact_kind": request.artifact_kind,
                "direction": request.direction,
                "attempt_id": provider_result.metadata.attempt_id,
                "requested_model": provider_result.metadata.requested_model,
                "response_id": provider_result.metadata.response_id,
                "outcome": "failed",
            },
        )
        raise
    return artifact_content, review_notes, provider_result.metadata


def _generated_json(
    request: DraftGenerationRequest,
    provider: DraftProvider,
    artifact: dict[str, Any],
    review_notes: str,
    result: dict[str, Any],
    provider_metadata: ProviderCallMetadata,
) -> GeneratedDraft:
    validated = result.get("validatedArtifact")
    draft_hash = validated.get("contentHash") if isinstance(validated, dict) else None
    if not isinstance(draft_hash, str) or not SHA256_PATTERN.fullmatch(draft_hash):
        raise DraftGenerationError("Validator result is missing a valid content hash")
    return _generated(
        request,
        provider,
        artifact,
        review_notes,
        result,
        draft_hash,
        provider_metadata,
    )


def _generated(
    request: DraftGenerationRequest,
    provider: DraftProvider,
    artifact: str | dict[str, Any],
    review_notes: str,
    validation_result: dict[str, Any] | None,
    draft_hash: str,
    provider_metadata: ProviderCallMetadata,
) -> GeneratedDraft:
    bound_notes = (
        "# Generated Draft Review Context\n\n"
        f"Artifact content hash: `{draft_hash}`\n\n"
        f"Provider: `{provider.name}`\n\n"
        f"Artifact kind: `{request.artifact_kind}`\n\n"
        "---\n\n"
        f"{review_notes.strip()}\n"
    )
    generated = GeneratedDraft(
        request=request,
        provider_name=provider.name,
        artifact=artifact,
        review_notes=bound_notes,
        validation_result=validation_result,
        content_hash=draft_hash,
        provider_metadata=provider_metadata,
    )
    LOGGER.info(
        "Generated IR Draft",
        extra={
            "component": "draft_generation",
            "task_id": request.task_id,
            "provider": provider.name,
            "artifact_kind": request.artifact_kind,
            "direction": request.direction,
            "attempt_id": provider_metadata.attempt_id,
            "requested_model": provider_metadata.requested_model,
            "response_id": provider_metadata.response_id,
            "outcome": "succeeded",
        },
    )
    return generated


def _text_context(content: str) -> DraftGenerationContext:
    return DraftGenerationContext(
        source_content=content,
        source_content_type="text/markdown",
    )


def _json_context(
    content: dict[str, Any],
    rule_package: RulePackage,
) -> DraftGenerationContext:
    return DraftGenerationContext(
        source_content=canonical_json_bytes(content).decode("utf-8"),
        source_content_type="application/json",
        rule_package_content=canonical_json_bytes(rule_package.documents).decode("utf-8"),
        rule_package_version=rule_package.version,
    )


def _require_pending_draft(artifact: dict[str, Any], *, label: str) -> None:
    review = artifact.get("review")
    if artifact.get("status") != "DRAFT":
        raise DraftGenerationError(f"{label} provider output must use status=DRAFT")
    if not isinstance(review, dict) or review.get("status") != "PENDING":
        raise DraftGenerationError(f"{label} provider output must use review.status=PENDING")
    if review.get("reviewer") is not None or review.get("reviewedAt") is not None:
        raise DraftGenerationError(f"{label} pending review cannot contain reviewer metadata")


def _require_matching_request_identity(
    artifact: dict[str, Any],
    *,
    expected: dict[str, str | None],
    label: str,
) -> None:
    for property_name, expected_value in expected.items():
        if artifact.get(property_name) != expected_value:
            raise DraftGenerationError(
                f"{label} Draft {property_name} must match the request selector"
            )


def _require_valid_draft_result(result: dict[str, Any], *, label: str) -> None:
    summary = result.get("summary")
    if not isinstance(summary, dict) or summary.get("errorCount") != 0:
        raise DraftGenerationError(f"{label} Draft must pass structural validation with zero errors")
    if result.get("finalEligible") is not False:
        raise DraftGenerationError(f"{label} Draft must remain ineligible for the trusted chain")
    issues = result.get("issues")
    codes = (
        {item.get("code") for item in issues if isinstance(item, dict)}
        if isinstance(issues, list)
        else set()
    )
    required = {"ARTIFACT_NOT_FINAL", "REVIEW_NOT_APPROVED"}
    if not required.issubset(codes):
        raise DraftGenerationError(f"{label} Draft is missing lifecycle blocking issues")


def _require_released_rule_package(rule_package: RulePackage) -> None:
    if not isinstance(rule_package, RulePackage) or rule_package.status != "RELEASED":
        raise DraftGenerationError("Draft generator requires a validated RELEASED rule package")


def _validate_docir_structure(content: str) -> None:
    required_headings = (
        "# Interface",
        "# Envelope",
        "# Message: ASSEMBLY",
        "# Message: PARSE",
    )
    for heading in required_headings:
        if content.count(heading) != 1:
            raise DraftGenerationError(f"DocIR Draft must contain exactly one {heading} section")
    if "| Message Format | XML |" not in content:
        raise DraftGenerationError("DocIR Draft must declare Message Format XML")
    sections = {
        heading: content.index(heading)
        for heading in required_headings
    }
    ordered = sorted(sections.items(), key=lambda item: item[1])
    for index, (heading, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(content)
        section = content[start:end]
        if "## Metadata" not in section:
            raise DraftGenerationError(f"DocIR {heading} section must contain a Metadata table")
        if heading != "# Interface" and "## Fields" not in section:
            raise DraftGenerationError(f"DocIR {heading} section must contain a Fields table")


def _request_from_case(value: Any, *, label: str) -> DraftGenerationRequest:
    if not isinstance(value, dict):
        raise DraftGenerationError(f"{label} must be an object")
    unknown = set(value) - CASE_REQUEST_PROPERTIES
    if unknown:
        raise DraftGenerationError(f"{label} has unknown properties: {', '.join(sorted(unknown))}")
    required = {"artifactKind", "sourceHash"}
    missing = required - set(value)
    if missing:
        raise DraftGenerationError(f"{label} is missing properties: {', '.join(sorted(missing))}")
    return DraftGenerationRequest(
        task_id="fixture-case-validation",
        artifact_kind=value.get("artifactKind"),
        source_hash=value.get("sourceHash"),
        direction=value.get("direction"),
        standard_version=value.get("standardVersion"),
        template_id=value.get("templateId"),
        template_version=value.get("templateVersion"),
        rule_package_version=value.get("rulePackageVersion"),
    )


def _strict_json_object(text: str, *, label: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise DraftGenerationError(f"{label} must be UTF-8 text")
    if text.startswith("\ufeff"):
        raise DraftGenerationError(f"{label} must be UTF-8 without BOM")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_number,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise DraftGenerationError(f"{label} must contain strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DraftGenerationError(f"{label} JSON root must be an object")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object property: {key}")
        result[key] = value
    return result


def _reject_non_finite_number(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _read_utf8_text(path: Path) -> str:
    if not path.is_file():
        raise DraftGenerationError(f"fixture file does not exist: {path}")
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        raise DraftGenerationError(f"fixture file must be UTF-8 without BOM: {path.name}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DraftGenerationError(f"fixture file must be valid UTF-8: {path.name}") from exc


def _require_exact_properties(value: dict[str, Any], allowed: set[str], *, label: str) -> None:
    missing = allowed - set(value)
    unknown = set(value) - allowed
    if missing:
        raise DraftGenerationError(f"{label} is missing properties: {', '.join(sorted(missing))}")
    if unknown:
        raise DraftGenerationError(f"{label} has unknown properties: {', '.join(sorted(unknown))}")


def _fingerprint_key(value: dict[str, str]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _text_hash(value: str) -> str:
    if not isinstance(value, str):
        raise DraftGenerationError("text input must be a string")
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"
