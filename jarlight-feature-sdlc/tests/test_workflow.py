"""Сценарні офлайн-тести оркестрації jarlight-feature-sdlc із підмінною моделлю."""

from __future__ import annotations

from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agent import build_workflow
from app.baseline import build_solo_agent
from app.coordinator import build_coordinator
from app.nodes import MAX_ROUNDS
from tests.fixtures import (
    BAD_BUNDLE,
    BAL_APPROVE,
    BAL_REVISE,
    GOOD_BUNDLE,
    PLAN_CLARIFY,
    PLAN_READY,
    QA_APPROVE,
    SOLO_GOOD,
    VALID_TASK,
)
from tests.scripted import ScriptedLlm


async def _run(agent, prompt: str) -> tuple[dict, list[dict]]:
    runner = InMemoryRunner(agent=agent, app_name="test_jarlight")
    session = await runner.session_service.create_session(
        app_name="test_jarlight", user_id="dev"
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    trace = []
    async for event in runner.run_async(
        user_id="dev", session_id=session.id, new_message=msg
    ):
        node = (event.node_info.path or "").split("/")[-1] if event.node_info else ""
        route = event.actions.route if event.actions else None
        trace.append({"author": event.author, "node": node, "route": route})
    final = await runner.session_service.get_session(
        app_name="test_jarlight", user_id="dev", session_id=session.id
    )
    return dict(final.state), trace


async def test_happy_path_parallel_join_approves_on_first_draft() -> None:
    llm = ScriptedLlm(
        model="scripted",
        script={
            "jarlight_feature_architect": [PLAN_READY],
            "jarlight_unity_implementer": [GOOD_BUNDLE],
            "jarlight_balance_reviewer": [BAL_APPROVE],
            "jarlight_ecs_qa_reviewer": [QA_APPROVE],
        },
    )
    wf = build_workflow(llm, kb_search=lambda _: "<fragment>RGB rule</fragment>", use_kb_agent=False)
    state, trace = await _run(wf, VALID_TASK)

    assert state["stop_reason"] == "approved"
    assert state["drafts"] == 1
    assert state["task_key"] == "JL-24"
    assert state["pr_draft"]["branch"] == "feat/jl-24-prism-splitter"
    assert any(t["node"].startswith("reviews") for t in trace)
    assert len(llm.calls) == 4


async def test_revise_then_approve_cycle_passes_feedback() -> None:
    llm = ScriptedLlm(
        model="scripted",
        script={
            "jarlight_feature_architect": [PLAN_READY],
            "jarlight_unity_implementer": [GOOD_BUNDLE, GOOD_BUNDLE],
            "jarlight_balance_reviewer": [BAL_REVISE, BAL_APPROVE],
            "jarlight_ecs_qa_reviewer": [QA_APPROVE, QA_APPROVE],
        },
    )
    wf = build_workflow(llm, kb_search=lambda _: "NOT_FOUND", use_kb_agent=False)
    state, _ = await _run(wf, VALID_TASK)

    assert state["stop_reason"] == "approved"
    assert state["drafts"] == 2
    assert "Magenta" in state["review_feedback"]
    assert len(llm.calls) == 7


async def test_loop_bound_stops_at_max_drafts() -> None:
    llm = ScriptedLlm(
        model="scripted",
        script={
            "jarlight_feature_architect": [PLAN_READY],
            "jarlight_unity_implementer": [GOOD_BUNDLE],
            "jarlight_balance_reviewer": [BAL_REVISE],
            "jarlight_ecs_qa_reviewer": [QA_APPROVE],
        },
    )
    wf = build_workflow(llm, kb_search=lambda _: "NOT_FOUND", use_kb_agent=False)
    state, _ = await _run(wf, VALID_TASK)

    assert state["stop_reason"] == "max_drafts"
    assert state["drafts"] == MAX_ROUNDS
    assert "# draft: [JL-24]" in state["report"]


async def test_lint_failure_routes_back_without_calling_reviewers() -> None:
    llm = ScriptedLlm(
        model="scripted",
        script={
            "jarlight_feature_architect": [PLAN_READY],
            "jarlight_unity_implementer": [BAD_BUNDLE, GOOD_BUNDLE],
            "jarlight_balance_reviewer": [BAL_APPROVE],
            "jarlight_ecs_qa_reviewer": [QA_APPROVE],
        },
    )
    wf = build_workflow(llm, kb_search=lambda _: "NOT_FOUND", use_kb_agent=False)
    state, _ = await _run(wf, VALID_TASK)

    assert state["stop_reason"] == "approved"
    assert state["drafts"] == 2
    assert llm.calls.count("jarlight_unity_implementer") == 2
    assert llm.calls.count("jarlight_balance_reviewer") == 1
    assert llm.calls.count("jarlight_ecs_qa_reviewer") == 1


async def test_short_invalid_input_rejected_with_zero_llm_calls() -> None:
    llm = ScriptedLlm(model="scripted", script={})
    wf = build_workflow(llm, kb_search=lambda _: "NOT_FOUND", use_kb_agent=False)
    state, _ = await _run(wf, "hi")

    assert state["stop_reason"] == "rejected_invalid_input"
    assert len(llm.calls) == 0


async def test_needs_clarification_stops_before_implementer() -> None:
    llm = ScriptedLlm(
        model="scripted",
        script={
            "jarlight_feature_architect": [PLAN_CLARIFY],
        },
    )
    wf = build_workflow(llm, kb_search=lambda _: "NOT_FOUND", use_kb_agent=False)
    state, _ = await _run(wf, "JL-29: Додати якийсь цікавий бонус у JarLight якомога швидше.")

    assert state["stop_reason"] == "needs_clarification"
    assert "Запитання до геймдизайнера" in state["report"]
    assert llm.calls == ["jarlight_feature_architect"]


async def test_kb_researcher_invokes_search_knowledge_tool() -> None:
    seen_queries = []

    def fake_search(q: str) -> str:
        seen_queries.append(q)
        return '<fragment source="[[Призми дисперсії#Вступ]]">Білий промінь ділиться на RGB.</fragment>'

    llm = ScriptedLlm(
        model="scripted",
        script={
            "jarlight_kb_researcher": ["Знайдено правило: [[Призми дисперсії#Вступ]]."],
            "jarlight_feature_architect": [PLAN_READY],
            "jarlight_unity_implementer": [GOOD_BUNDLE],
            "jarlight_balance_reviewer": [BAL_APPROVE],
            "jarlight_ecs_qa_reviewer": [QA_APPROVE],
        },
        tool_calls={
            "jarlight_kb_researcher": [("search_knowledge", {"query": "призми дисперсії RGB"})]
        },
    )
    wf = build_workflow(llm, kb_search=fake_search, use_kb_agent=True)
    state, _ = await _run(wf, VALID_TASK)

    assert seen_queries == ["призми дисперсії RGB"]
    assert "[[Призми дисперсії#Вступ]]" in state["kb_context"]
    assert state["stop_reason"] == "approved"


async def test_baseline_solo_agent_runs_offline() -> None:
    llm = ScriptedLlm(
        model="scripted",
        script={"jarlight_solo_developer": [SOLO_GOOD]},
    )
    solo = build_solo_agent(llm)
    state, _ = await _run(solo, VALID_TASK)

    assert state["solo_result"]["task_key"] == "JL-24"
    assert len(llm.calls) == 1


def test_coordinator_configures_single_turn_subagents() -> None:
    llm = ScriptedLlm(model="scripted", script={})
    coord = build_coordinator(llm)
    assert len(coord.sub_agents) == 4
    assert all(sub.mode == "single_turn" for sub in coord.sub_agents)
