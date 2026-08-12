from __future__ import annotations

import json
import logging
import sys
from threading import Event
from types import SimpleNamespace

import httpx
import pytest

import bank_config_compiler.openai_chat_provider as openai_chat_provider
from bank_config_compiler.docir_draft import DocIRDraftError
from bank_config_compiler.draft_generation import (
    DraftProviderDiagnosticError,
    DraftGenerationContext,
    DraftGenerationError,
    DraftGenerationRequest,
    generate_docir_draft,
)
from bank_config_compiler.openai_chat_provider import (
    OpenAIChatDraftProvider,
    build_chat_messages,
)


class FakeCompletions:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response: object) -> None:
        self.completions = FakeCompletions(response)
        self.chat = SimpleNamespace(completions=self.completions)


class QueuedFakeCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("unexpected extra chat completion call")
        return self.responses.pop(0)


class QueuedFakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.completions = QueuedFakeCompletions(responses)
        self.chat = SimpleNamespace(completions=self.completions)


class FailingClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs: object) -> SimpleNamespace:
        raise TimeoutError("SECRET-BANK-PAYLOAD")


def chat_chunk(
    content: str | None = None,
    *,
    finish_reason: str | None = None,
    response_id: str = "chatcmpl-test",
    model: str = "qwen-test-snapshot",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=response_id,
        model=model,
        choices=[
            SimpleNamespace(
                index=0,
                finish_reason=finish_reason,
                delta=SimpleNamespace(content=content),
            )
        ],
        usage=None,
    )


def usage_chunk(
    *,
    response_id: str = "chatcmpl-test",
    model: str = "qwen-test-snapshot",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=response_id,
        model=model,
        choices=[],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


def chat_stream(content: str) -> list[SimpleNamespace]:
    split_at = max(1, len(content) // 2)
    return [
        chat_chunk(content[:split_at]),
        chat_chunk(content[split_at:]),
        chat_chunk(finish_reason="stop"),
        usage_chunk(),
    ]


class InterruptedStream:
    def __iter__(self):
        yield chat_chunk('{"artifact":"SECRET-BANK-PAYLOAD')
        raise TimeoutError("SECRET-BANK-PAYLOAD")


class NonContentStreamUntilClosed:
    def __init__(self) -> None:
        self.closed = Event()

    def __iter__(self):
        for _ in range(300):
            yield chat_chunk()
            if self.closed.wait(0.01):
                raise RuntimeError("stream closed by deadline watchdog")
        raise RuntimeError("stream self-terminated after test safety timeout")

    def close(self) -> None:
        self.closed.set()


class BlockingCreateClient:
    def __init__(self) -> None:
        self.closed = Event()
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.closed.wait(3.0):
            raise RuntimeError("client closed by deadline watchdog")
        raise RuntimeError("client self-terminated after test safety timeout")

    def close(self) -> None:
        self.closed.set()


def model_metadata(key: str, value: str, review_note: str = "") -> dict[str, str]:
    return {"key": key, "value": value, "reviewNote": review_note}


def model_field(index: str, item: str) -> dict[str, str]:
    return {
        "index": index,
        "or": "",
        "item": item,
        "multiplicity": "[1..1]",
        "type": "Object" if "." not in index else "String",
        "required": "Y",
        "description": f"{item} description",
        "preValidation": "source format",
        "platformValidation": "platform check",
        "review": "",
    }


def model_tree_node(item: str, *, children: list[dict] | None = None) -> dict:
    return {
        "item": item,
        "nodeKind": "XML_ATTRIBUTE" if item.startswith("@") else "XML_ELEMENT",
        "children": children or [],
    }


def model_semantics(field: dict[str, str], *, selector: str) -> dict[str, str]:
    return {
        "selector": selector,
        **{
            key: value
            for key, value in field.items()
            if key not in {"index", "item"}
        },
    }


def docir_model_artifact() -> dict:
    return {
        "contractVersion": "docir-extraction/v1",
        "interface": {
            "metadata": [
                model_metadata("Interface Code", "b2e9999"),
                model_metadata("Interface Name", "测试接口"),
                model_metadata("Message Format", "XML"),
                model_metadata("Version", "120"),
                model_metadata("Source Document", "raw-doc.md"),
            ]
        },
        "sourceContext": ["只保留明确来源。"],
        "envelope": {
            "metadata": [
                model_metadata("Envelope Name", "bocb2e"),
                model_metadata("Root Path", "bocb2e", "derived path"),
                model_metadata("Applies To", "ASSEMBLY, PARSE"),
                model_metadata("Evidence Scope", "explicit source"),
            ],
            "fields": [model_field("1", "bocb2e")],
        },
        "assembly": {
            "metadata": [
                model_metadata("Message Name", "test-rq"),
                model_metadata("Function Type", "ASSEMBLY"),
                model_metadata("Root Path", "bocb2e/trans/test-rq", "derived path"),
                model_metadata("Description", "请求报文"),
            ],
            "fields": [model_field("2", "test-rq"), model_field("2.1", "request")],
            "conditions": ["仅保留来源明确的请求条件。"],
        },
        "parse": {
            "metadata": [
                model_metadata("Message Name", "test-rs"),
                model_metadata("Function Type", "PARSE"),
                model_metadata("Root Path", "bocb2e/trans/test-rs", "derived path"),
                model_metadata("Description", "响应报文"),
            ],
            "fields": [model_field("3", "test-rs"), model_field("3.1", "status")],
            "conditions": ["仅保留来源明确的响应条件。"],
        },
    }


def docir_segment_responses(
    *,
    assembly_count: int = 27,
    parse_count: int = 10,
    batch_size: int = 16,
) -> list[dict]:
    extraction = docir_model_artifact()
    extraction["assembly"]["fields"] = [
        model_field("2", "test-rq"),
        *[
            model_field(f"2.{index}", f"request{index}")
            for index in range(1, assembly_count)
        ],
    ]
    extraction["parse"]["fields"] = [
        model_field("3", "test-rs"),
        *[
            model_field(f"3.{index}", f"response{index}")
            for index in range(1, parse_count)
        ],
    ]
    interface_envelope = {
        "contractVersion": "docir-interface-envelope-tree-segment/v1",
        "interface": extraction["interface"],
        "sourceContext": extraction["sourceContext"],
        "envelope": {
            "metadata": extraction["envelope"]["metadata"],
            "nodes": [
                {
                    **model_tree_node(extraction["envelope"]["fields"][0]["item"]),
                    **{
                        key: value
                        for key, value in extraction["envelope"]["fields"][0].items()
                        if key not in {"index", "item"}
                    },
                }
            ],
        },
    }
    outline = {
        "contractVersion": "docir-messages-tree-segment/v1",
        "assembly": {
            "metadata": extraction["assembly"]["metadata"],
            "conditions": extraction["assembly"]["conditions"],
            "nodes": [
                model_tree_node(
                    extraction["assembly"]["fields"][0]["item"],
                    children=[
                        model_tree_node(row["item"])
                        for row in extraction["assembly"]["fields"][1:]
                    ],
                )
            ],
        },
        "parse": {
            "metadata": extraction["parse"]["metadata"],
            "conditions": extraction["parse"]["conditions"],
            "nodes": [
                model_tree_node(
                    extraction["parse"]["fields"][0]["item"],
                    children=[
                        model_tree_node(row["item"])
                        for row in extraction["parse"]["fields"][1:]
                    ],
                )
            ],
        },
    }
    responses = [interface_envelope, outline]
    for direction, section_name in (("ASSEMBLY", "assembly"), ("PARSE", "parse")):
        fields = extraction[section_name]["fields"]
        semantics = [
            model_semantics(
                row,
                selector=(
                    f"{section_name}:1"
                    if position == 0
                    else f"{section_name}:1.{position}"
                ),
            )
            for position, row in enumerate(fields)
        ]
        for start in range(0, len(semantics), batch_size):
            responses.append(
                {
                    "contractVersion": "docir-field-semantics-segment/v1",
                    "direction": direction,
                    "batchIndex": start // batch_size + 1,
                    "fields": semantics[start : start + batch_size],
                }
            )
    return responses


def queued_docir_client(
    *,
    assembly_count: int = 27,
    parse_count: int = 10,
    batch_size: int = 16,
) -> QueuedFakeClient:
    return QueuedFakeClient(
        [
            chat_stream(json.dumps(response, ensure_ascii=False))
            for response in docir_segment_responses(
                assembly_count=assembly_count,
                parse_count=parse_count,
                batch_size=batch_size,
            )
        ]
    )


def test_openai_chat_provider_segments_docir_with_default_bounded_batches() -> None:
    client = queued_docir_client()
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-012",
        client=client,
    )
    request = DraftGenerationRequest(
        task_id="phase0-test",
        artifact_kind="docir",
        source_hash="sha256:" + "1" * 64,
    )
    context = DraftGenerationContext(
        source_content="# Raw bank document\n",
        source_content_type="text/markdown",
    )

    result = provider.generate(request, context)

    assert len(client.completions.calls) == 5
    assert [call.segment for call in result.metadata.calls] == [
        "interface-envelope",
        "messages-outline",
        "assembly-fields-001",
        "assembly-fields-002",
        "parse-fields-001",
    ]
    assert result.metadata.docir_field_batch_size == 16
    assert result.metadata.total_tokens == 150
    for call in client.completions.calls:
        assert "# Raw bank document" in call["messages"][1]["content"]
        assert "Prompt contract: draft-prompt/v13" in call["messages"][1]["content"]
    envelope = json.loads(result.response_text)
    assert envelope["contractVersion"] == "draft-provider-response/v1"
    assert "| 2.26 |" in envelope["artifactContent"]
    assert "| 3.9 |" in envelope["artifactContent"]


def test_openai_chat_provider_respects_configured_docir_batch_size() -> None:
    client = queued_docir_client(batch_size=8)
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-012",
        docir_field_batch_size=8,
        client=client,
    )

    provider.generate(
        DraftGenerationRequest(
            task_id="phase0-test",
            artifact_kind="docir",
            source_hash="sha256:" + "1" * 64,
        ),
        DraftGenerationContext(
            source_content="# Raw bank document\n",
            source_content_type="text/markdown",
        ),
    )

    assert len(client.completions.calls) == 8


def test_openai_chat_provider_fails_fast_after_invalid_field_segment() -> None:
    responses = docir_segment_responses(assembly_count=2, parse_count=2)
    responses[2]["fields"][0]["selector"] = "assembly:unexpected-root"
    client = QueuedFakeClient(
        [chat_stream(json.dumps(response, ensure_ascii=False)) for response in responses]
    )
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-012",
        client=client,
    )

    with pytest.raises(DraftProviderDiagnosticError, match="target selectors") as caught:
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )

    evidence = caught.value.evidence
    assert evidence is not None
    assert len(client.completions.calls) == 3
    assert evidence.failure_stage == "segment-validation"
    assert evidence.failed_segment == "assembly-fields-001"
    assert [call.metadata.outcome for call in evidence.calls] == [
        "succeeded",
        "succeeded",
        "failed",
    ]


def test_openai_chat_provider_preserves_prior_calls_when_a_later_stream_fails() -> None:
    segments = docir_segment_responses(assembly_count=2, parse_count=2)
    client = QueuedFakeClient(
        [
            chat_stream(json.dumps(segments[0], ensure_ascii=False)),
            chat_stream(json.dumps(segments[1], ensure_ascii=False)),
            InterruptedStream(),
        ]
    )
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-012",
        client=client,
    )

    with pytest.raises(DraftProviderDiagnosticError, match="chat stream failed") as caught:
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )

    evidence = caught.value.evidence
    assert evidence is not None
    assert len(client.completions.calls) == 3
    assert evidence.failure_stage == "stream"
    assert evidence.failed_segment == "assembly-fields-001"
    assert [call.metadata.outcome for call in evidence.calls] == [
        "succeeded",
        "succeeded",
        "failed",
    ]
    assert evidence.calls[0].response_text == json.dumps(
        segments[0], ensure_ascii=False
    )
    assert evidence.calls[1].response_text == json.dumps(
        segments[1], ensure_ascii=False
    )
    assert evidence.calls[2].response_text == '{"artifact":"SECRET-BANK-PAYLOAD'


def test_openai_chat_provider_enforces_absolute_deadline_on_non_content_stream(
    caplog: pytest.LogCaptureFixture,
) -> None:
    segments = docir_segment_responses(assembly_count=2, parse_count=2)
    stalled_stream = NonContentStreamUntilClosed()
    client = QueuedFakeClient(
        [
            chat_stream(json.dumps(segments[0], ensure_ascii=False)),
            stalled_stream,
            chat_stream(json.dumps(segments[2], ensure_ascii=False)),
        ]
    )
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-018",
        timeout_seconds=1,
        client=client,
    )

    with caplog.at_level(logging.WARNING), pytest.raises(
        DraftProviderDiagnosticError,
        match="absolute deadline",
    ) as caught:
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )

    evidence = caught.value.evidence
    assert evidence is not None
    assert len(client.completions.calls) == 2
    assert stalled_stream.closed.is_set()
    assert evidence.failure_stage == "stream"
    assert evidence.failed_segment == "messages-outline"
    assert evidence.error_type == "ProviderCallDeadlineExceeded"
    assert "timeout_seconds=1" in evidence.failure_detail
    assert "parsed_chunks=" in evidence.failure_detail
    assert "content_chunks=0" in evidence.failure_detail
    assert evidence.response_text is None
    assert evidence.calls[0].response_text == json.dumps(segments[0], ensure_ascii=False)
    assert evidence.calls[1].metadata.response_id == "chatcmpl-test"
    deadline_record = next(
        record
        for record in caplog.records
        if record.getMessage() == "IR Draft provider subcall deadline exceeded"
    )
    assert deadline_record.task_id == "phase0-test"
    assert deadline_record.segment == "messages-outline"
    assert deadline_record.timeout_seconds == 1.0
    assert deadline_record.parsed_chunk_count > 0
    assert deadline_record.content_chunk_count == 0


def test_openai_chat_provider_deadline_includes_stream_creation() -> None:
    client = BlockingCreateClient()
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-018",
        timeout_seconds=1,
        client=client,
    )

    with pytest.raises(
        DraftProviderDiagnosticError,
        match="absolute deadline",
    ) as caught:
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )

    evidence = caught.value.evidence
    assert evidence is not None
    assert len(client.calls) == 1
    assert client.closed.is_set()
    assert evidence.failure_stage == "request"
    assert evidence.failed_segment == "interface-envelope"
    assert evidence.error_type == "ProviderCallDeadlineExceeded"
    assert "parsed_chunks=0" in evidence.failure_detail
    assert "content_chunks=0" in evidence.failure_detail


def test_openai_chat_provider_preserves_early_read_timeout_classification() -> None:
    class EarlyReadTimeoutStream:
        def __iter__(self):
            yield chat_chunk()
            raise httpx.ReadTimeout("offline early read timeout")

    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-018",
        timeout_seconds=600,
        client=FakeClient(EarlyReadTimeoutStream()),
    )

    with pytest.raises(DraftProviderDiagnosticError, match="ReadTimeout") as caught:
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )

    evidence = caught.value.evidence
    assert evidence is not None
    assert evidence.failure_stage == "stream"
    assert evidence.error_type == "ReadTimeout"
    assert "absolute deadline" not in evidence.failure_detail


def test_openai_chat_provider_records_merge_failure_after_all_subcalls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = queued_docir_client(assembly_count=2, parse_count=2)
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-012",
        client=client,
    )

    def fail_merge(*args: object, **kwargs: object) -> dict:
        raise DocIRDraftError("forced merge failure")

    monkeypatch.setattr(
        "bank_config_compiler.openai_chat_provider.merge_docir_semantic_segments",
        fail_merge,
    )

    with pytest.raises(DraftProviderDiagnosticError, match="forced merge failure") as caught:
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )

    evidence = caught.value.evidence
    assert evidence is not None
    assert len(client.completions.calls) == 4
    assert evidence.failure_stage == "merge-validation"
    assert evidence.failed_segment is None
    assert all(call.metadata.outcome == "succeeded" for call in evidence.calls)


def test_openai_chat_provider_uses_explicit_context_and_returns_v1_envelope() -> None:
    client = queued_docir_client(assembly_count=2, parse_count=2)
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        timeout_seconds=600,
        client=client,
    )
    request = DraftGenerationRequest(
        task_id="phase0-test",
        artifact_kind="docir",
        source_hash="sha256:" + "1" * 64,
    )
    context = DraftGenerationContext(
        source_content="# Raw bank document\n",
        source_content_type="text/markdown",
    )

    result = provider.generate(request, context)

    envelope = json.loads(result.response_text)
    assert envelope["contractVersion"] == "draft-provider-response/v1"
    assert envelope["artifactKind"] == "docir"
    assert "| 2.1 |  | 　`request1` | [1..1] | String | Y |" in envelope["artifactContent"]
    assert "## 固定检查清单" in envelope["reviewNotes"]
    assert "Envelope.Metadata[Root Path]: derived path" in envelope["reviewNotes"]
    assert "ASSEMBLY.Metadata[Root Path]: derived path" in envelope["reviewNotes"]
    assert result.metadata.attempt_id == "docir-001"
    assert result.metadata.response_id is None
    assert result.metadata.requested_model == "qwen-test-snapshot"
    assert result.metadata.response_model == "qwen-test-snapshot"
    assert result.metadata.total_tokens == 120
    assert [call.segment for call in result.metadata.calls] == [
        "interface-envelope",
        "messages-outline",
        "assembly-fields-001",
        "parse-fields-001",
    ]

    for call in client.completions.calls:
        assert call["model"] == "qwen-test-snapshot"
        assert call["stream"] is True
        assert call["stream_options"] == {"include_usage": True}
        assert call["response_format"] == {"type": "json_object"}
        messages = call["messages"]
        assert "# Raw bank document" in messages[1]["content"]
        assert "Final" not in messages[1]["content"]


def test_openai_chat_provider_allows_complete_streams_before_absolute_deadline() -> None:
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-018",
        timeout_seconds=1,
        client=queued_docir_client(assembly_count=2, parse_count=2),
    )

    result = provider.generate(
        DraftGenerationRequest(
            task_id="phase0-test",
            artifact_kind="docir",
            source_hash="sha256:" + "1" * 64,
        ),
        DraftGenerationContext(
            source_content="# Raw bank document\n",
            source_content_type="text/markdown",
        ),
    )

    assert [call.segment for call in result.metadata.calls] == [
        "interface-envelope",
        "messages-outline",
        "assembly-fields-001",
        "parse-fields-001",
    ]


def test_docir_prompt_requests_structured_extraction_and_preserves_source_scope() -> None:
    request = DraftGenerationRequest(
        task_id="phase0-test",
        artifact_kind="docir",
        source_hash="sha256:" + "1" * 64,
    )
    context = DraftGenerationContext(
        source_content="# Raw bank document\n",
        source_content_type="text/markdown",
    )

    messages = build_chat_messages(request, context)

    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]
    normalized_system_prompt = " ".join(system_prompt.split())
    assert "Prompt contract: draft-prompt/v13" in user_prompt
    assert "Segment: interface-envelope" in user_prompt
    assert "docir-interface-envelope-tree-segment/v1" in system_prompt
    assert "`contractVersion`, `interface`, `sourceContext`, `envelope`" in system_prompt
    assert "`sourceContext` is a non-empty JSON array of non-empty strings" in system_prompt
    assert "complete shared Envelope structure" in system_prompt
    assert "validated outline selector" not in system_prompt
    assert "outer provider" in system_prompt
    assert "separate review-notes" in system_prompt
    assert "Do not emit Markdown" in system_prompt
    assert "XML item name" in system_prompt
    assert "`[1..1]`" in system_prompt
    assert "`[0..1]`" in system_prompt
    assert "`[0..1000]`" in system_prompt
    for field_type in ("`String`", "`Boolean`", "`Date`", "`Decimal`", "`Object`"):
        assert field_type in system_prompt
    for required_value in ("`Y`", "`N`", "`C`"):
        assert required_value in system_prompt
    assert "maximum without a minimum" in normalized_system_prompt
    assert "leave it empty" in normalized_system_prompt
    assert "Generic XML examples" in normalized_system_prompt
    assert "other transaction codes" in normalized_system_prompt
    assert "out-of-scope transaction fields" in normalized_system_prompt
    assert "Simplified Chinese" in system_prompt
    assert "b2e0061" not in system_prompt
    assert "serverdt" not in system_prompt
    assert "golden" not in user_prompt.lower()
    assert "workspace" not in user_prompt.lower()


def test_docir_segment_prompts_keep_stage_responsibilities_separate() -> None:
    request = DraftGenerationRequest(
        task_id="phase0-test",
        artifact_kind="docir",
        source_hash="sha256:" + "1" * 64,
    )
    context = DraftGenerationContext(
        source_content="# Raw bank document\n",
        source_content_type="text/markdown",
    )
    outline_prompt = openai_chat_provider._DocIRSegmentPrompt(
        segment="messages-outline",
        contract_version="docir-messages-tree-segment/v1",
    )
    detail_prompt = openai_chat_provider._DocIRSegmentPrompt(
        segment="assembly-fields-001",
        contract_version="docir-field-semantics-segment/v1",
        direction="ASSEMBLY",
        batch_index=1,
        target_outline=[
            {
                "selector": "assembly:1",
                "item": "request-root",
                "nodeKind": "XML_ELEMENT",
            }
        ],
    )

    interface_system = " ".join(build_chat_messages(request, context)[0]["content"].split())
    outline_system = " ".join(build_chat_messages(
        request,
        context,
        docir_segment=outline_prompt,
    )[0]["content"].split())
    detail_system = " ".join(build_chat_messages(
        request,
        context,
        docir_segment=detail_prompt,
    )[0]["content"].split())

    for system_prompt in (interface_system, outline_system, detail_system):
        assert "Every JSON object property must appear exactly once" in system_prompt

    assert "Envelope scope ends at the `trans` container" in interface_system
    assert "Do not include transaction-specific request or response roots" in interface_system
    assert (
        "must not name or enumerate transaction-specific request or response fields"
        in interface_system
    )
    assert "Never return `index`, `selector`" in interface_system
    assert "Child array order" in interface_system
    assert "Do not return `assembly`, `parse`, message metadata or conditions" in interface_system
    assert "Omitted semantic properties mean unknown" in interface_system
    assert "materializer injects the fixed Review marker" in interface_system
    assert "assembly/parse: Message Name" not in interface_system
    assert "Conditions contain only" not in interface_system

    assert "Return one combined ordered semantic tree" in outline_system
    assert "Every node has exactly `item`, `nodeKind`, and `children`" in outline_system
    assert "Never return `index`, `selector`" in outline_system
    assert "Do not return semantic detail properties" in outline_system
    assert "Do not include shared Envelope nodes" in outline_system
    assert "semantic string properties" not in outline_system
    assert "interface: Interface Code" not in outline_system

    assert "The validated semantic selector" in detail_system
    assert '\"direction\": \"ASSEMBLY\"' in detail_system
    assert '\"batchIndex\": 1' in detail_system
    assert "REQUESTED_DIRECTION" not in detail_system
    assert "REQUESTED_BATCH_INDEX" not in detail_system
    assert "Each field requires only `selector`" in detail_system
    assert "Do not return `item`, `nodeKind`, `index`" in detail_system
    assert "Metadata rows have exactly" not in detail_system
    assert "Conditions contain only" not in detail_system


def test_openai_chat_provider_rejects_old_docir_model_envelope_with_complete_evidence() -> None:
    old_envelope = json.dumps(
        {"artifact": docir_model_artifact(), "reviewNotes": ["确认字段。"]},
        ensure_ascii=False,
    )
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FakeClient(chat_stream(old_envelope)),
    )

    with pytest.raises(DraftProviderDiagnosticError, match="unknown properties") as caught:
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )

    evidence = caught.value.evidence
    assert evidence is not None
    assert evidence.failure_stage == "segment-validation"
    assert evidence.failed_segment == "interface-envelope"
    assert evidence.response_complete is True
    assert evidence.response_text == old_envelope
    assert evidence.finish_reason == "stop"
    assert evidence.metadata.response_id == "chatcmpl-test"
    assert evidence.metadata.total_tokens == 30
    assert len(evidence.calls) == 1
    assert evidence.calls[0].metadata.outcome == "failed"


def test_openai_chat_provider_rejects_markdown_docir_model_artifact() -> None:
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FakeClient(chat_stream(json.dumps("# Interface\n"))),
    )

    with pytest.raises(DraftGenerationError, match="root must be an object"):
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )


def test_orchestration_reports_docir_extraction_validation_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FakeClient(
            chat_stream(
                json.dumps({"contractVersion": "docir-extraction/v1"})
            )
        ),
    )

    with caplog.at_level(logging.WARNING), pytest.raises(
        DraftGenerationError,
        match=(
            "DocIR interface-envelope segment is invalid: "
            "DocIR interface-envelope tree segment has invalid properties"
        ),
    ) as caught:
        generate_docir_draft(
            raw_doc="# Raw bank document\n",
            provider=provider,
            task_id="phase0-test",
        )

    assert "missing properties" in str(caught.value)
    assert caplog.records[-1].failure_detail == (
        "DocIR interface-envelope segment is invalid: "
        "DocIR interface-envelope tree segment has invalid properties "
        "(missing properties: envelope, interface, sourceContext)"
    )


def test_openai_chat_provider_serializes_json_artifact_without_double_encoded_prompt_output() -> None:
    client = FakeClient(
        chat_stream(
            json.dumps(
                {
                    "artifact": {"contractVersion": "schemair/v2", "status": "DRAFT"},
                    "reviewNotes": "Pending review.",
                }
            )
        )
    )
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="schemair-001",
        client=client,
    )
    request = DraftGenerationRequest(
        task_id="phase0-test",
        artifact_kind="schemair",
        source_hash="sha256:" + "2" * 64,
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
    )
    context = DraftGenerationContext(
        source_content="# Final DocIR\n",
        source_content_type="text/markdown",
    )

    result = provider.generate(request, context)

    envelope = json.loads(result.response_text)
    assert json.loads(envelope["artifactContent"]) == {
        "contractVersion": "schemair/v2",
        "status": "DRAFT",
    }


def test_openai_chat_provider_constructs_sdk_client_without_automatic_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def openai_client(**kwargs: object) -> FakeClient:
        captured.update(kwargs)
        return FakeClient(chat_stream('{"artifact":"x","reviewNotes":"review"}'))

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=openai_client))

    OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1/",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        timeout_seconds=45,
    )

    assert captured == {
        "api_key": "test-key",
        "base_url": "https://example.invalid/v1",
        "timeout": 45.0,
        "max_retries": 0,
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"base_url": "http://example.invalid/v1"}, "HTTPS"),
        ({"base_url": "https://user:secret@example.invalid/v1"}, "credentials"),
        ({"timeout_seconds": 0}, "between 1 and 3600"),
        ({"attempt_id": "bad attempt"}, "attempt_id"),
    ],
)
def test_openai_chat_provider_rejects_unsafe_runtime_configuration(
    kwargs: dict[str, object],
    message: str,
) -> None:
    parameters: dict[str, object] = {
        "api_key": "test-key",
        "base_url": "https://example.invalid/v1",
        "model": "qwen-test-snapshot",
        "attempt_id": "docir-001",
        "client": FakeClient(chat_stream('{"artifact":"x","reviewNotes":"review"}')),
    }
    parameters.update(kwargs)

    with pytest.raises(DraftGenerationError, match=message):
        OpenAIChatDraftProvider(**parameters)


def test_openai_chat_provider_rejects_truncated_or_invalid_response() -> None:
    response = [
        chat_chunk('{"artifact":"x","reviewNotes":"review"}'),
        chat_chunk(finish_reason="length"),
    ]
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FakeClient(response),
    )

    with pytest.raises(DraftGenerationError, match="finish with stop"):
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )


def test_openai_chat_provider_rejects_response_from_a_different_model() -> None:
    response = chat_stream('{"artifact":"x","reviewNotes":"review"}')
    response[0].model = "different-model"
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FakeClient(response),
    )

    with pytest.raises(DraftGenerationError, match="requested model"):
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )


def test_openai_chat_failure_is_logged_with_safe_attempt_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FailingClient(),
    )

    with caplog.at_level(logging.WARNING), pytest.raises(DraftGenerationError) as caught:
        generate_docir_draft(
            raw_doc="# Raw bank document\n",
            provider=provider,
            task_id="phase0-test",
        )

    assert "SECRET-BANK-PAYLOAD" not in str(caught.value)
    assert "SECRET-BANK-PAYLOAD" not in caplog.text
    assert "TimeoutError" in str(caught.value)
    record = caplog.records[-1]
    assert record.attempt_id == "docir-001"
    assert record.requested_model == "qwen-test-snapshot"
    evidence = caught.value.evidence
    assert evidence is not None
    assert evidence.failure_stage == "request"
    assert evidence.response_complete is False
    assert evidence.response_text is None
    assert evidence.error_type == "TimeoutError"


def test_interrupted_stream_does_not_publish_or_log_partial_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FakeClient(InterruptedStream()),
    )

    with caplog.at_level(logging.WARNING), pytest.raises(
        DraftProviderDiagnosticError
    ) as caught:
        generate_docir_draft(
            raw_doc="# Raw bank document\n",
            provider=provider,
            task_id="phase0-test",
        )

    assert "SECRET-BANK-PAYLOAD" not in str(caught.value)
    assert "SECRET-BANK-PAYLOAD" not in caplog.text
    evidence = caught.value.evidence
    assert evidence is not None
    assert evidence.failure_stage == "stream"
    assert evidence.response_complete is False
    assert evidence.response_text == '{"artifact":"SECRET-BANK-PAYLOAD'
    assert evidence.error_type == "TimeoutError"


def test_openai_chat_provider_requires_terminal_usage_chunk() -> None:
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FakeClient(
            [
                chat_chunk('{"artifact":"x","reviewNotes":"review"}'),
                chat_chunk(finish_reason="stop"),
            ]
        ),
    )

    with pytest.raises(DraftGenerationError, match="usage"):
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )


def test_openai_chat_provider_preserves_response_when_usage_values_are_invalid() -> None:
    response_text = json.dumps(docir_model_artifact())
    response = chat_stream(response_text)
    response[-1].usage.prompt_tokens = "invalid"
    provider = OpenAIChatDraftProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1",
        model="qwen-test-snapshot",
        attempt_id="docir-001",
        client=FakeClient(response),
    )

    with pytest.raises(DraftProviderDiagnosticError, match="usage.prompt_tokens") as caught:
        provider.generate(
            DraftGenerationRequest(
                task_id="phase0-test",
                artifact_kind="docir",
                source_hash="sha256:" + "1" * 64,
            ),
            DraftGenerationContext(
                source_content="# Raw bank document\n",
                source_content_type="text/markdown",
            ),
        )

    evidence = caught.value.evidence
    assert evidence is not None
    assert evidence.failure_stage == "stream"
    assert evidence.response_text == response_text
    assert evidence.metadata.prompt_tokens is None


def test_standard_prompt_contains_canonical_rules_but_no_workspace_or_golden_paths() -> None:
    request = DraftGenerationRequest(
        task_id="phase0-test",
        artifact_kind="standard",
        source_hash="sha256:" + "1" * 64,
        standard_id="b2e0061-assembly-standard",
        direction="ASSEMBLY",
        standard_version="v1",
        rule_package_version="v1",
    )
    context = DraftGenerationContext(
        source_content='{"contractVersion":"schemair/v2"}',
        source_content_type="application/json",
        rule_package_content='{"schema.yaml":{"status":"RELEASED"}}',
        rule_package_version="v1",
    )

    messages = build_chat_messages(request, context)
    user_message = messages[1]["content"]

    assert '"direction": "ASSEMBLY"' in user_message
    assert '<RELEASED_RULE_PACKAGE_JSON>' in user_message
    assert '"schema.yaml":{"status":"RELEASED"}' in user_message
    assert "workspace" not in user_message.lower()
    assert "golden" not in user_message.lower()
