from __future__ import annotations

import json
import logging
import sys
from types import SimpleNamespace

import pytest

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


def test_openai_chat_provider_uses_explicit_context_and_returns_v1_envelope() -> None:
    client = FakeClient(chat_stream(json.dumps(docir_model_artifact())))
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
    assert "| 2.1 |  | 　`request` | [1..1] | String | Y |" in envelope["artifactContent"]
    assert "## 固定检查清单" in envelope["reviewNotes"]
    assert "Envelope.Metadata[Root Path]: derived path" in envelope["reviewNotes"]
    assert "ASSEMBLY.Metadata[Root Path]: derived path" in envelope["reviewNotes"]
    assert result.metadata.attempt_id == "docir-001"
    assert result.metadata.response_id == "chatcmpl-test"
    assert result.metadata.requested_model == "qwen-test-snapshot"
    assert result.metadata.response_model == "qwen-test-snapshot"
    assert result.metadata.total_tokens == 30

    call = client.completions.calls[0]
    assert call["model"] == "qwen-test-snapshot"
    assert call["stream"] is True
    assert call["stream_options"] == {"include_usage": True}
    assert call["response_format"] == {"type": "json_object"}
    messages = call["messages"]
    assert "# Raw bank document" in messages[1]["content"]
    assert "Final" not in messages[1]["content"]


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
    assert "Prompt contract: draft-prompt/v7" in user_prompt
    assert "`docir-extraction/v1` JSON object" in system_prompt
    assert "exactly the extraction root" in system_prompt
    assert '"contractVersion": "docir-extraction/v1"' in system_prompt
    assert '"metadata"' in system_prompt
    assert '"sourceContext"' in system_prompt
    assert '"fields"' in system_prompt
    assert '"conditions"' in system_prompt
    assert '"artifact"' not in system_prompt
    assert '"reviewNotes"' not in system_prompt
    assert "Do not emit Markdown" in system_prompt
    assert "plain XML item name" in system_prompt
    assert "Envelope field indexes are rooted at `1`" in system_prompt
    assert "ASSEMBLY field indexes are rooted at `2`" in system_prompt
    assert "PARSE field indexes are rooted at `3`" in system_prompt
    assert "`[1..1]`, `[0..1]` or `[0..1000]`" in system_prompt
    assert "`String`, `Boolean`, `Date`, `Decimal` or `Object`" in system_prompt
    assert "exactly `Y`, `N` or `C`" in system_prompt
    assert "maximum without a minimum" in system_prompt
    assert "response field without explicit requiredness" in system_prompt
    assert "leave that cell empty" in system_prompt
    assert "generic XML example" in system_prompt
    assert "different transaction code" in system_prompt
    assert "example-only transaction fields" in system_prompt
    assert "Simplified Chinese" in system_prompt
    assert "b2e0061" not in system_prompt
    assert "serverdt" not in system_prompt
    assert "golden" not in user_prompt.lower()
    assert "workspace" not in user_prompt.lower()


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
    assert evidence.failure_stage == "docir-extraction"
    assert evidence.response_complete is True
    assert evidence.response_text == old_envelope
    assert evidence.finish_reason == "stop"
    assert evidence.metadata.response_id == "chatcmpl-test"
    assert evidence.metadata.total_tokens == 30


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
        match="DocIR chat extraction is invalid: DocIR extraction has invalid properties",
    ) as caught:
        generate_docir_draft(
            raw_doc="# Raw bank document\n",
            provider=provider,
            task_id="phase0-test",
        )

    assert "missing properties" in str(caught.value)
    assert caplog.records[-1].failure_detail == (
        "DocIR chat extraction is invalid: DocIR extraction has invalid properties "
        "(missing properties: assembly, envelope, interface, parse, sourceContext)"
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
