from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol


class SegmentDisposition(str, Enum):
    ACCEPT = "ACCEPT"
    NORMALIZED = "NORMALIZED"
    INVALID_DRAFT = "INVALID_DRAFT"
    RETRY_SEGMENT = "RETRY_SEGMENT"
    HARD_FAIL = "HARD_FAIL"


@dataclass(frozen=True, slots=True)
class NormalizationDiagnostic:
    segment: str
    code: str
    action: str
    severity: str
    selector: str | None = None
    path: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "segment": self.segment,
            "selector": self.selector,
            "path": self.path,
            "code": self.code,
            "action": self.action,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class SegmentSpec:
    segment_id: str
    contract_version: str
    payload: Mapping[str, Any]
    payload_hash: str
    selector_hash: str | None = None
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SegmentFingerprint:
    source_hash: str
    request_hash: str
    prompt_contract_version: str
    segment_contract_version: str
    requested_model: str
    endpoint_fingerprint: str
    generation_parameters_hash: str
    segment_payload_hash: str
    value: str

    @classmethod
    def build(
        cls,
        *,
        source_hash: str,
        request: Mapping[str, Any],
        prompt_contract_version: str,
        segment_contract_version: str,
        requested_model: str,
        endpoint_fingerprint: str,
        generation_parameters: Mapping[str, Any],
        segment_payload: Mapping[str, Any],
    ) -> SegmentFingerprint:
        request_hash = _canonical_hash(request)
        generation_parameters_hash = _canonical_hash(generation_parameters)
        segment_payload_hash = _canonical_hash(segment_payload)
        components = {
            "sourceHash": source_hash,
            "requestHash": request_hash,
            "promptContractVersion": prompt_contract_version,
            "segmentContractVersion": segment_contract_version,
            "requestedModel": requested_model,
            "endpointFingerprint": endpoint_fingerprint,
            "generationParametersHash": generation_parameters_hash,
            "segmentPayloadHash": segment_payload_hash,
        }
        return cls(
            source_hash=source_hash,
            request_hash=request_hash,
            prompt_contract_version=prompt_contract_version,
            segment_contract_version=segment_contract_version,
            requested_model=requested_model,
            endpoint_fingerprint=endpoint_fingerprint,
            generation_parameters_hash=generation_parameters_hash,
            segment_payload_hash=segment_payload_hash,
            value=_canonical_hash(components),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "sourceHash": self.source_hash,
            "requestHash": self.request_hash,
            "promptContractVersion": self.prompt_contract_version,
            "segmentContractVersion": self.segment_contract_version,
            "requestedModel": self.requested_model,
            "endpointFingerprint": self.endpoint_fingerprint,
            "generationParametersHash": self.generation_parameters_hash,
            "segmentPayloadHash": self.segment_payload_hash,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class SegmentValidationResult:
    disposition: SegmentDisposition
    value: dict[str, Any] | None
    diagnostics: tuple[NormalizationDiagnostic, ...] = ()
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ReusableSegment:
    segment_id: str
    response_text: str
    response_hash: str
    model_response: dict[str, Any]
    origin_attempt_id: str
    origin_call_sequence: int
    fingerprint: SegmentFingerprint
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ResumeSegmentCandidate:
    segment_id: str
    response_text: str
    response_hash: str
    origin_attempt_id: str
    origin_call_sequence: int
    segment_contract_version: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    fingerprint: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ResumeAttemptEvidence:
    contract_version: str
    task_id: str
    source_hash: str
    requested_model: str
    endpoint_fingerprint: str
    prompt_contract_version: str
    schemair_field_batch_size: int
    attempt_id: str
    selectors: Mapping[str, Any] | None
    segments: tuple[ResumeSegmentCandidate, ...]


@dataclass(frozen=True, slots=True)
class SegmentCallResult:
    model_response: dict[str, Any]
    response_text: str
    call_evidence: Any


class SegmentCallFailure(Exception):
    def __init__(
        self,
        detail: str,
        *,
        retryable: bool,
        call_evidence: Any,
        retry_delay_seconds: float = 0.0,
        failure_stage: str = "request",
        error_type: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.retryable = retryable
        self.call_evidence = call_evidence
        self.retry_delay_seconds = retry_delay_seconds
        self.failure_stage = failure_stage
        self.error_type = error_type


class SegmentPreCallFailure(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SegmentAttemptRecord:
    segment_id: str
    segment_attempt: int
    outcome: str
    call_evidence: Any
    response_text: str | None


@dataclass(frozen=True, slots=True)
class ResolvedSegment:
    spec: SegmentSpec
    source: str
    value: dict[str, Any]
    response_text: str
    response_hash: str
    fingerprint: SegmentFingerprint
    disposition: SegmentDisposition
    diagnostics: tuple[NormalizationDiagnostic, ...]
    origin_attempt_id: str
    origin_call_sequence: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True, slots=True)
class SegmentedExecutionResult:
    attempts: tuple[SegmentAttemptRecord, ...]
    segments: tuple[ResolvedSegment, ...]


class SegmentedExecutionFailure(Exception):
    def __init__(
        self,
        detail: str,
        *,
        spec: SegmentSpec,
        disposition: SegmentDisposition,
        attempts: tuple[SegmentAttemptRecord, ...],
        segments: tuple[ResolvedSegment, ...],
        cause: Exception | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.spec = spec
        self.disposition = disposition
        self.attempts = attempts
        self.segments = segments
        self.cause = cause


def execute_segment_plan(
    plan: tuple[SegmentSpec, ...],
    *,
    profile: SegmentedArtifactProfile,
    structure: Mapping[str, Any],
    fingerprints: Mapping[str, SegmentFingerprint],
    reusable_segments: Mapping[str, ReusableSegment],
    max_retries: int,
    current_attempt_id: str,
    before_call: Callable[[SegmentSpec, int], float],
    call_segment: Callable[[SegmentSpec, int, float], SegmentCallResult],
    wait: Callable[[float], None],
) -> SegmentedExecutionResult:
    """Execute a validated plan without knowing provider, workspace, or bank semantics."""

    by_id = {spec.segment_id: spec for spec in plan}
    unknown_reusable = sorted(reusable_segments.keys() - by_id.keys())
    if unknown_reusable:
        raise ValueError(
            "resume evidence contains unknown segments: " + ", ".join(unknown_reusable)
        )
    prevalidated: dict[str, tuple[ReusableSegment, SegmentValidationResult]] = {}
    for segment_id, reusable in reusable_segments.items():
        spec = by_id[segment_id]
        expected_fingerprint = fingerprints[segment_id]
        if reusable.fingerprint != expected_fingerprint:
            raise ValueError(f"resume fingerprint does not match segment: {segment_id}")
        if reusable.response_hash != _text_hash(reusable.response_text):
            raise ValueError(f"resume response hash does not match content: {segment_id}")
        validation = profile.validate_segment(
            spec, reusable.model_response, structure=structure
        )
        if validation.value is None or validation.disposition in {
            SegmentDisposition.RETRY_SEGMENT,
            SegmentDisposition.HARD_FAIL,
        }:
            raise ValueError(
                f"resume segment is not reusable: {segment_id}: {validation.detail}"
            )
        prevalidated[segment_id] = (reusable, validation)

    attempts: list[SegmentAttemptRecord] = []
    resolved: list[ResolvedSegment] = []
    for spec in plan:
        fingerprint = fingerprints[spec.segment_id]
        if spec.segment_id in prevalidated:
            reusable, validation = prevalidated[spec.segment_id]
            assert validation.value is not None
            resolved.append(
                ResolvedSegment(
                    spec=spec,
                    source="REUSED",
                    value=validation.value,
                    response_text=reusable.response_text,
                    response_hash=reusable.response_hash,
                    fingerprint=fingerprint,
                    disposition=validation.disposition,
                    diagnostics=validation.diagnostics,
                    origin_attempt_id=reusable.origin_attempt_id,
                    origin_call_sequence=reusable.origin_call_sequence,
                    prompt_tokens=reusable.prompt_tokens,
                    completion_tokens=reusable.completion_tokens,
                    total_tokens=reusable.total_tokens,
                )
            )
            continue

        for segment_attempt in range(1, max_retries + 2):
            try:
                timeout_seconds = before_call(spec, segment_attempt)
                call = call_segment(spec, segment_attempt, timeout_seconds)
            except SegmentPreCallFailure as exc:
                raise SegmentedExecutionFailure(
                    str(exc),
                    spec=spec,
                    disposition=SegmentDisposition.HARD_FAIL,
                    attempts=tuple(attempts),
                    segments=tuple(resolved),
                    cause=exc,
                ) from exc
            except SegmentCallFailure as exc:
                attempts.append(
                    SegmentAttemptRecord(
                        segment_id=spec.segment_id,
                        segment_attempt=segment_attempt,
                        outcome="failed",
                        call_evidence=exc.call_evidence,
                        response_text=getattr(exc.call_evidence, "response_text", None),
                    )
                )
                if exc.retryable and segment_attempt <= max_retries:
                    if exc.retry_delay_seconds > 0:
                        try:
                            wait(exc.retry_delay_seconds)
                        except SegmentPreCallFailure as wait_error:
                            raise SegmentedExecutionFailure(
                                str(wait_error),
                                spec=spec,
                                disposition=SegmentDisposition.HARD_FAIL,
                                attempts=tuple(attempts),
                                segments=tuple(resolved),
                                cause=wait_error,
                            ) from wait_error
                    continue
                raise SegmentedExecutionFailure(
                    exc.detail,
                    spec=spec,
                    disposition=SegmentDisposition.HARD_FAIL,
                    attempts=tuple(attempts),
                    segments=tuple(resolved),
                    cause=exc,
                ) from exc
            validation = profile.validate_segment(
                spec, call.model_response, structure=structure
            )
            accepted = validation.value is not None and validation.disposition in {
                SegmentDisposition.ACCEPT,
                SegmentDisposition.NORMALIZED,
                SegmentDisposition.INVALID_DRAFT,
            }
            attempts.append(
                SegmentAttemptRecord(
                    segment_id=spec.segment_id,
                    segment_attempt=segment_attempt,
                    outcome="succeeded" if accepted else "failed",
                    call_evidence=call.call_evidence,
                    response_text=call.response_text,
                )
            )
            if accepted:
                metadata = getattr(call.call_evidence, "metadata", call.call_evidence)
                assert validation.value is not None
                resolved.append(
                    ResolvedSegment(
                        spec=spec,
                        source="LIVE",
                        value=validation.value,
                        response_text=call.response_text,
                        response_hash=_text_hash(call.response_text),
                        fingerprint=fingerprint,
                        disposition=validation.disposition,
                        diagnostics=validation.diagnostics,
                        origin_attempt_id=current_attempt_id,
                        origin_call_sequence=len(attempts),
                        prompt_tokens=getattr(metadata, "prompt_tokens", None),
                        completion_tokens=getattr(metadata, "completion_tokens", None),
                        total_tokens=getattr(metadata, "total_tokens", None),
                    )
                )
                break
            if (
                validation.disposition == SegmentDisposition.RETRY_SEGMENT
                and segment_attempt <= max_retries
            ):
                continue
            raise SegmentedExecutionFailure(
                validation.detail or f"segment validation failed: {spec.segment_id}",
                spec=spec,
                disposition=SegmentDisposition.HARD_FAIL,
                attempts=tuple(attempts),
                segments=tuple(resolved),
            )
    return SegmentedExecutionResult(tuple(attempts), tuple(resolved))


class SegmentedArtifactProfile(Protocol):
    def build_segment_plan(
        self, structure: Mapping[str, Any], *, batch_size: int
    ) -> tuple[SegmentSpec, ...]: ...

    def validate_segment(
        self,
        spec: SegmentSpec,
        value: Any,
        *,
        structure: Mapping[str, Any],
    ) -> SegmentValidationResult: ...

    def merge(
        self,
        segments: Mapping[str, dict[str, Any]],
        *,
        structure: Mapping[str, Any],
        batch_size: int,
    ) -> dict[str, Any]: ...


def canonical_segment_hash(value: Mapping[str, Any]) -> str:
    return _canonical_hash(value)


def _canonical_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _text_hash(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"
