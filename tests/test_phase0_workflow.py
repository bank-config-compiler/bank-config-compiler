from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from bank_config_compiler.configuration_rules import load_rule_package
from bank_config_compiler.workspace import (
    Phase0Selection,
    WorkspaceError,
    check_workspace,
    load_phase0_artifacts,
    phase0_workbook_path,
)


REPO_ROOT = Path(__file__).parents[1]
CHAIN_ROOT = REPO_ROOT / "samples" / "trusted-chain" / "b2eboc-b2e0061"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bank_config_compiler", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def copy_chain(tmp_path: Path) -> Path:
    workspace = tmp_path / "trusted-chain"
    workspace.mkdir()
    for name in ("schemair-final.json", "schemair-validation-result.json"):
        shutil.copy2(CHAIN_ROOT / name, workspace / name)
    for direction in ("assembly", "parse"):
        shutil.copytree(
            CHAIN_ROOT / "standards" / direction / "v1",
            workspace / "standards" / direction / "v1",
        )
        shutil.copytree(
            CHAIN_ROOT / "templates" / direction / "v1",
            workspace / "templates" / direction / f"b2e0061-{direction}-common" / "v1",
            ignore=shutil.ignore_patterns("*.xlsx"),
        )
    return workspace


def assembly_selection() -> Phase0Selection:
    return direction_selection("assembly")


def direction_selection(direction: str) -> Phase0Selection:
    return Phase0Selection(
        direction=direction,
        standard_version="v1",
        template_id=f"b2e0061-{direction}-common",
        template_version="v1",
    )


def phase0_args(workspace: Path, direction: str = "assembly") -> list[str]:
    template_id = f"b2e0061-{direction}-common"
    return [
        "--workspace",
        str(workspace),
        "--direction",
        direction,
        "--standard-version",
        "v1",
        "--template-id",
        template_id,
        "--template-version",
        "v1",
        "--standard-rule-package",
        str(REPO_ROOT / "configuration-rules" / "v1"),
        "--template-rule-package",
        str(REPO_ROOT / "configuration-rules" / "v2"),
    ]


def test_phase0_selection_loads_fixed_six_artifact_chain(tmp_path: Path) -> None:
    workspace = copy_chain(tmp_path)
    selection = assembly_selection()

    artifacts = load_phase0_artifacts(workspace, selection)

    assert artifacts.standard["direction"] == "ASSEMBLY"
    assert artifacts.template["templateId"] == selection.template_id
    assert phase0_workbook_path(workspace, selection) == (
        workspace
        / "templates"
        / "assembly"
        / "b2e0061-assembly-common"
        / "v1"
        / "configuration-workbook.xlsx"
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"direction": "ASSEMBLY"}, "direction"),
        ({"standard_version": "1"}, "standard_version"),
        ({"template_id": "B2E0061"}, "template_id"),
        ({"template_version": "latest"}, "template_version"),
    ],
)
def test_phase0_selection_rejects_aliases_and_unstable_values(kwargs: dict, message: str) -> None:
    values = {
        "direction": "assembly",
        "standard_version": "v1",
        "template_id": "b2e0061-assembly-common",
        "template_version": "v1",
    }
    values.update(kwargs)

    with pytest.raises(WorkspaceError, match=message):
        Phase0Selection(**values)


def test_phase0_workspace_check_is_read_only(tmp_path: Path) -> None:
    workspace = copy_chain(tmp_path)
    selection = assembly_selection()
    output = phase0_workbook_path(workspace, selection)

    checked = check_workspace(
        workspace,
        profile="phase0",
        selection=selection,
        standard_rule_package=load_rule_package(REPO_ROOT / "configuration-rules" / "v1"),
        template_rule_package=load_rule_package(REPO_ROOT / "configuration-rules" / "v2"),
    )

    assert checked == 6
    assert not output.exists()


def test_cli_phase0_check_requires_explicit_selectors(tmp_path: Path) -> None:
    workspace = copy_chain(tmp_path)

    result = run_cli("check", "--workspace", str(workspace), "--profile", "phase0")

    assert result.returncode == 2
    assert "--direction" in result.stderr


@pytest.mark.parametrize("direction", ["assembly", "parse"])
def test_cli_phase0_check_and_generate_workbook(tmp_path: Path, direction: str) -> None:
    workspace = copy_chain(tmp_path)
    args = phase0_args(workspace, direction)
    selection = direction_selection(direction)

    checked = run_cli("check", "--profile", "phase0", *args)
    assert checked.returncode == 0, checked.stderr
    assert "(6 artifacts)" in checked.stdout
    assert not phase0_workbook_path(workspace, selection).exists()

    generated = run_cli("generate-workbook", *args, "--standard-action", "CREATE")
    assert generated.returncode == 0, generated.stderr
    output = phase0_workbook_path(workspace, selection)
    assert output.is_file()
    assert str(output) in generated.stdout

    refused = run_cli("generate-workbook", *args, "--standard-action", "CREATE")
    assert refused.returncode == 2
    assert "already exists" in refused.stderr

    overwritten = run_cli(
        "generate-workbook",
        *args,
        "--standard-action",
        "UPDATE",
        "--overwrite",
    )
    assert overwritten.returncode == 0, overwritten.stderr


def test_phase0_loader_rejects_selector_artifact_mismatch(tmp_path: Path) -> None:
    workspace = copy_chain(tmp_path)
    selection = assembly_selection()
    standard_path = workspace / "standards" / "assembly" / "v1" / "standard-final.json"
    content = standard_path.read_text(encoding="utf-8").replace('"direction": "ASSEMBLY"', '"direction": "PARSE"', 1)
    standard_path.write_text(content, encoding="utf-8", newline="")

    with pytest.raises(WorkspaceError, match="selector"):
        load_phase0_artifacts(workspace, selection)


def test_cli_phase0_check_rejects_standard_template_rule_path_swap(tmp_path: Path) -> None:
    workspace = copy_chain(tmp_path)
    args = phase0_args(workspace)
    standard_index = args.index("--standard-rule-package") + 1
    template_index = args.index("--template-rule-package") + 1
    args[standard_index], args[template_index] = args[template_index], args[standard_index]

    result = run_cli("check", "--profile", "phase0", *args)

    assert result.returncode == 2
    assert "RULE_PACKAGE_VERSION_MISMATCH" in result.stderr
    assert not phase0_workbook_path(workspace, assembly_selection()).exists()
