"""Базова лінія (один агент) для порівняння якості й вартості з командою Workflow."""

from __future__ import annotations

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from .schemas import SoloFeatureResult

SOLO_INSTRUCTION = """
ROLE: jarlight_solo_developer
LANGUAGE: Ukrainian for prose, valid C# and JSON for code/presets.
TASK: For a given JarLight GDD feature task, evaluate readiness and immediately produce ECS changes, level preset JSON, C# snippets, and Unity NUnit tests in one response.
RULES:
1. If vague (e.g. missing mechanics/win rules), set readiness_status="needs_clarification" and list clarification_questions.
2. Otherwise provide concrete Unity ECS/Burst changes, valid level_preset_json, C# snippet, and NUnit tests with [Test]/[UnityTest] and Assert.
"""


def build_solo_agent(model: BaseLlm | str) -> Agent:
    """Створює одиночного агента з еквівалентною вихідною схемою SoloFeatureResult."""
    return Agent(
        name="jarlight_solo_agent",
        model=model,
        instruction=SOLO_INSTRUCTION,
        output_schema=SoloFeatureResult,
        output_key="solo_result",
    )
