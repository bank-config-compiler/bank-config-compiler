from __future__ import annotations

import hashlib
import json
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
