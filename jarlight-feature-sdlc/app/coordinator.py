"""Альтернативна оркестрація через координатора з експертами single_turn (крок 12)."""

from __future__ import annotations

from google.adk import Agent
from google.adk.models.base_llm import BaseLlm

from .agents import build_agents

COORDINATOR_INSTRUCTION = """
ROLE: jarlight_sdlc_coordinator
LANGUAGE: Ukrainian.
TASK: Coordinate building a JarLight Unity feature package using four single_turn sub-agents:
1. feature_architect — evaluate GDD readiness and produce plan.
2. unity_implementer — generate ECS changes, C# snippet, level JSON preset, and Unity NUnit tests.
3. game_balance_reviewer — review optical physics, RGB spectrum, and Par Moves balance.
4. unity_ecs_qa_reviewer — review Burst/ECS safety, ray bounds, JSON validity, and NUnit coverage.

Workflow:
- First delegate to feature_architect. If readiness_status is "needs_clarification", stop and summarize questions.
- Otherwise delegate ONCE to unity_implementer.
- Next delegate ONCE to game_balance_reviewer and ONCE to unity_ecs_qa_reviewer. If either returns "revise", delegate back to unity_implementer AT MOST ONCE without repeating reviews indefinitely, then immediately return the final concise Markdown summary.
"""


def build_coordinator(model: BaseLlm | str) -> Agent:
    """Динамічний координатор над тими самими чотирма експертами в режимі mode='single_turn'."""
    experts = build_agents(model, mode="single_turn")
    for sub in experts.values():
        sub.disallow_transfer_to_parent = False
        sub.disallow_transfer_to_peers = True

    return Agent(
        name="jarlight_coordinator",
        description="Динамічний координатор розробки фіч JarLight для порівняння зі сталим Workflow.",
        model=model,
        instruction=COORDINATOR_INSTRUCTION,
        sub_agents=[
            experts["feature_architect"],
            experts["unity_implementer"],
            experts["game_balance_reviewer"],
            experts["unity_ecs_qa_reviewer"],
        ],
    )
