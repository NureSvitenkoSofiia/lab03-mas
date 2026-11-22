"""Тестові JSON-фікстури для офлайн-перевірки оркестрації jarlight-feature-sdlc."""

from __future__ import annotations

import json

VALID_TASK = (
    "JL-24: Додати елемент PrismSplitter у Unity ECS із розщепленням білого "
    "променя на R/G/B, лімітом 8 відбиттів, пресетом рівня та NUnit тестами."
)

PLAN_READY = json.dumps(
    {
        "task_key": "JL-24",
        "title": "Призма дисперсії PrismSplitter у Unity ECS",
        "readiness_status": "ready",
        "readiness_score": 5,
        "clarification_questions": [],
        "affected_systems": ["Optics", "ECS", "LevelDesign"],
        "acceptance_criteria": [
            "Given білий промінь, When влучає в PrismSplitter, Then генеруються промені R, G і B під кутом 60 градусів",
            "Given 8 відбиттів, When перевищено ліміт рекурсії, Then трасування зупиняється без зависання",
        ],
        "implementation_steps": [
            "Додати PrismComponent : IComponentData",
            "Оновити Burst-систему RayTraceSystem",
        ],
        "test_plan": ["EditMode тест розщеплення RGB", "Перевірка max_bounces=8"],
    },
    ensure_ascii=False,
)

PLAN_CLARIFY = json.dumps(
    {
        "task_key": "JL-29",
        "title": "Невизначений бонус для кристалів",
        "readiness_status": "needs_clarification",
        "readiness_score": 2,
        "clarification_questions": [
            "Як саме новий бонус змінює спектр RGB або Par Moves?",
            "Чи сумісний бонус із розчинюваними банками та кам яними перешкодами?",
        ],
        "affected_systems": ["Mechanics"],
        "acceptance_criteria": [],
        "implementation_steps": [],
        "test_plan": [],
    },
    ensure_ascii=False,
)

GOOD_BUNDLE = json.dumps(
    {
        "task_key": "JL-24",
        "branch_name": "feat/jl-24-prism-splitter",
        "summary": "Реалізовано Burst-безпечний PrismSplitter у Unity ECS з розщепленням RGB та обмеженням глибини.",
        "ecs_changes": [
            "Створено PrismSplitterComponent : IComponentData",
            "Оновлено RayTraceJob з урахуванням ліміту max_bounces = 8",
        ],
        "level_design_changes": ["Оновлено LevelPreset_14 з нормативом Par Moves = 7"],
        "csharp_snippets": (
            "[BurstCompile]\n"
            "public partial struct RayTraceSystem : ISystem {\n"
            "    public void OnUpdate(ref SystemState state) { /* maxBounces = 8 */ }\n"
            "}"
        ),
        "unity_nunit_tests": (
            "using NUnit.Framework;\n"
            "public class PrismSplitterTests {\n"
            "    [Test]\n"
            "    public void SplitWhiteBeam_ProducesRgbRays() {\n"
            "        Assert.AreEqual(3, 3);\n"
            "    }\n"
            "}"
        ),
        "level_preset_json": json.dumps(
            {"levelId": "JL-24", "parMoves": 7, "maxBounces": 8, "prisms": [{"q": 1, "r": -1}]}
        ),
        "assumptions": ["[[Призми дисперсії та розщеплення світлових пучків#Вступ]]"],
    },
    ensure_ascii=False,
)

BAD_BUNDLE = json.dumps(
    {
        "task_key": "JL-24",
        "branch_name": "feat/jl-24-broken",
        "summary": "Чернетка з порушенням правил Burst та без валідного NUnit тесту.",
        "ecs_changes": ["Оновлено PrismComponent"],
        "level_design_changes": ["Тимчасовий рівень"],
        "csharp_snippets": "void BadUpdate() { var go = GameObject.Find(\"Laser\"); }",
        "unity_nunit_tests": "void EmptyCheck() { }",
        "level_preset_json": "{broken_json",
        "assumptions": [],
    },
    ensure_ascii=False,
)

BAL_APPROVE = json.dumps(
    {
        "verdict": "approve",
        "optics_integrity_score": 5,
        "balance_score": 5,
        "issues": [],
        "required_fixes": [],
    },
    ensure_ascii=False,
)

BAL_REVISE = json.dumps(
    {
        "verdict": "revise",
        "optics_integrity_score": 3,
        "balance_score": 3,
        "issues": ["Не перевірено комбінацію червоного і синього променів у пурпурний (Magenta)."],
        "required_fixes": ["Додати NUnit-тест адитивного змішування R+B після призми."],
    },
    ensure_ascii=False,
)

QA_APPROVE = json.dumps(
    {
        "verdict": "approve",
        "burst_safety_score": 5,
        "test_coverage_score": 5,
        "missing_scenarios": [],
        "required_fixes": [],
    },
    ensure_ascii=False,
)

SOLO_GOOD = json.dumps(
    {
        "task_key": "JL-24",
        "title": "Призма PrismSplitter",
        "readiness_status": "ready",
        "clarification_questions": [],
        "branch_name": "feat/jl-24-solo",
        "ecs_changes": ["Додано PrismComponent"],
        "level_design_changes": ["Par Moves = 7"],
        "csharp_snippets": "public struct PrismComponent : IComponentData { public int MaxBounces; }",
        "unity_nunit_tests": "[Test] public void TestPrism() { Assert.IsTrue(true); }",
        "level_preset_json": "{\"levelId\": \"JL-24\"}",
        "assumptions": [],
    },
    ensure_ascii=False,
)
