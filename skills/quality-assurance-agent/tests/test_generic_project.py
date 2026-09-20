"""A 档：非 maven/npm 项目归为 generic，流程能跑通，命令由上游（AI）填。

判别力：每条断言都对应一处放松/新增逻辑，回滚该逻辑时对应测试会红。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from qa_core.project_manifest import (
    ProjectDiscoveryError,
    discover_projects,
    resolve_target_project,
)


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _case() -> dict:
    return {
        "id": "TC-P0-001",
        "priority": "P0",
        "title": "下单接口",
        "module": "order",
        "type": "business",
        "layer": "api",
        "automation": "automated",
        "status": "confirmed",
        "businessActor": "普通用户",
        "operationPath": "POST /api/orders",
        "preconditions": ["余额充足"],
        "steps": ["发起下单"],
        "expected": ["下单成功"],
        "businessAssertions": ["响应 code=200"],
        "traceability": ["RISK-P0-001"],
    }


def test_go_project_discovered_as_generic(tmp_path):
    """只有 go.mod 的项目应被识别为 generic，而不是被忽略。"""
    write(tmp_path / "svc" / "go.mod", "module example.com/svc\n\ngo 1.22\n")
    projects = discover_projects(tmp_path)
    kinds = {p.kind for p in projects}
    assert "generic" in kinds, "go.mod 项目必须被识别为 generic"
    generic = [p for p in projects if p.kind == "generic"][0]
    assert generic.name == "svc"


def test_python_project_resolves_without_error(tmp_path):
    """纯 Python 项目（pyproject.toml）resolve_target_project 应返回 generic，而不抛 ProjectDiscoveryError。"""
    write(tmp_path / "api" / "pyproject.toml", "[project]\nname = \"api\"\n")
    project = resolve_target_project(tmp_path, _case(), "api")
    assert project.kind == "generic"


def test_empty_repo_still_raises(tmp_path):
    """既无 pom/package.json 也无任何 generic 标志时，仍应抛 ProjectDiscoveryError。"""
    write(tmp_path / "README.md", "nothing runnable here\n")
    with pytest.raises(ProjectDiscoveryError):
        resolve_target_project(tmp_path, _case(), "api")


def test_maven_preferred_over_generic_for_api_layer(tmp_path):
    """同一 repo 内 maven 与 generic 并存时，api 层必须优先选 maven，generic 只兜底。"""
    write(
        tmp_path / "backend" / "pom.xml",
        "<project><artifactId>backend</artifactId></project>",
    )
    write(tmp_path / "svc" / "go.mod", "module example.com/svc\n\ngo 1.22\n")
    project = resolve_target_project(tmp_path, _case(), "api")
    assert project.kind == "maven", "有 maven 项目时 api 层不应落到 generic"


def _minimal_cases(cases: list[dict]) -> dict:
    return {"status": "confirmed", "version": "1.0", "cases": cases}


def test_generic_spec_task_has_empty_command_and_flag(qa, tmp_path):
    """generic 项目生成的 spec-task：command/targetFile 为空，且打 needsManualCommand 标记。"""
    write(tmp_path / "svc" / "go.mod", "module example.com/svc\n\ngo 1.22\n")
    cases = _minimal_cases([_case()])
    result = qa.generate_spec_tasks_data(cases, repo=tmp_path)

    tasks = result["tasks"]
    assert tasks, "应生成 spec-task"
    for task in tasks:
        assert task["command"] == "", "generic 项目不应硬造执行命令"
        assert task["targetFile"] == "", "generic 项目不应硬造测试文件路径"
        assert task.get("needsManualCommand") is True, "generic task 必须标记 needsManualCommand"


def test_generic_passed_task_without_command_fails_gate(qa):
    """generic task 声称 passed 却 command 为空＝假通过，assert-completion 必须报 generic-command-missing。"""
    cases = _minimal_cases([_case()])
    spec_tasks = {
        "version": "1.0",
        "tasks": [
            {
                "id": "SPEC-TC-P0-001-API-001",
                "sourceCaseId": "TC-P0-001",
                "priority": "P0",
                "layer": "api",
                "implementationStatus": "implemented",
                "executionStatus": "passed",
                "command": "",
                "needsManualCommand": True,
                "traceability": ["RISK-ORDER-001"],
                "targetFile": "",
                "evidence": [{"type": "stdout", "content": "ok"}],
            }
        ],
    }
    result = qa.assert_completion_data(cases, spec_tasks, priorities={"P0"})
    types = {f["type"] for f in result["findings"]}
    assert "generic-command-missing" in types, "空 command 的 passed task 必须被门禁拦截"

