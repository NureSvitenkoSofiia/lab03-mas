"""Модульні тести детермінованих вузлів та валідатора Unity ECS JarLight."""

from __future__ import annotations

import json

from app.nodes import extract_task_key, validate_unity_bundle


def _valid_impl() -> dict:
    return {
        "task_key": "JL-24",
        "ecs_changes": ["Додано PrismComponent"],
        "csharp_snippets": "[BurstCompile] public struct PrismSystem : ISystem { public void OnUpdate() {} }",
        "unity_nunit_tests": "[Test] public void CheckSplit() { Assert.AreEqual(3, 3); }",
        "level_preset_json": json.dumps({"levelId": "JL-24", "parMoves": 7}),
    }


def test_extract_task_key() -> None:
    assert extract_task_key("Запит jl-42 щодо таймера") == "JL-42"
    assert extract_task_key("Без ідентифікатора") == "JL-NEW"


def test_validate_accepts_valid_unity_bundle() -> None:
    assert validate_unity_bundle(_valid_impl()) == []


def test_validate_blocks_gameobject_find_and_resources_load() -> None:
    impl = _valid_impl()
    impl["csharp_snippets"] = "void Update() { var x = GameObject.Find(\"Laser\"); var y = Resources.Load(\"A\"); }"
    errs = validate_unity_bundle(impl)
    assert any("GameObject.Find" in e for e in errs)


def test_validate_detects_hardcoded_api_key_and_unsafe() -> None:
    impl = _valid_impl()
    impl["csharp_snippets"] = "string key = \"AIzaSyDUMMYKEY1234567890ABCDEFG\"; unsafe { int* p; }"
    errs = validate_unity_bundle(impl)
    assert any("секрет" in e for e in errs)
    assert any("unsafe" in e for e in errs)


def test_validate_rejects_invalid_preset_json() -> None:
    impl = _valid_impl()
    impl["level_preset_json"] = "{invalid"
    errs = validate_unity_bundle(impl)
    assert any("JSON" in e for e in errs)


def test_validate_requires_nunit_test_and_assert() -> None:
    impl = _valid_impl()
    impl["unity_nunit_tests"] = "public void HelperMethod() { int x = 1; }"
    errs = validate_unity_bundle(impl)
    assert any("Assert" in e for e in errs)
