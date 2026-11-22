"""Запуск мультиагентної системи jarlight-feature-sdlc із термінала зі збереженням трасування."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

load_dotenv()

from app.agent import build_workflow, gemini


async def run_once(request_text: str, use_kb_agent: bool = True) -> dict:
    wf = build_workflow(gemini(), use_kb_agent=use_kb_agent)
    runner = InMemoryRunner(agent=wf, app_name="jarlight_cli")
    session = await runner.session_service.create_session(
        app_name="jarlight_cli", user_id="dev"
    )
    msg = types.Content(role="user", parts=[types.Part(text=request_text)])

    trace = []
    llm_calls: dict[str, int] = {}
    tokens = 0
    started = datetime.now()

    async for event in runner.run_async(
        user_id="dev", session_id=session.id, new_message=msg
    ):
        node = (event.node_info.path or "").split("/")[-1] if event.node_info else ""
        route = event.actions.route if event.actions else None
        text = "".join(p.text or "" for p in (event.content.parts if event.content and event.content.parts else []))
        if event.usage_metadata:
            llm_calls[event.author] = llm_calls.get(event.author, 0) + 1
            tokens += event.usage_metadata.total_token_count or 0
        trace.append(
            {
                "author": event.author,
                "node": node,
                "route": route,
                "preview": text[:160],
            }
        )

    final_session = await runner.session_service.get_session(
        app_name="jarlight_cli", user_id="dev", session_id=session.id
    )
    state = dict(final_session.state)
    elapsed = (datetime.now() - started).total_seconds()
    return {
        "request": request_text,
        "use_kb_agent": use_kb_agent,
        "elapsed_seconds": round(elapsed, 2),
        "tokens": tokens,
        "llm_calls": llm_calls,
        "stop_reason": state.get("stop_reason", ""),
        "drafts": state.get("drafts", 0),
        "task_key": state.get("task_key", ""),
        "trace": trace,
        "report": state.get("report", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI для JarLight Feature SDLC")
    parser.add_argument("request", help="Опис задачі GDD/Jira (JL-XX ...)")
    parser.add_argument(
        "--no-kb-agent",
        action="store_true",
        help="Використовувати детермінований retrieve_context замість kb_researcher",
    )
    args = parser.parse_args()

    result = asyncio.run(run_once(args.request, use_kb_agent=not args.no_kb_agent))
    runs_dir = Path("runs")
    runs_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    key = (result.get("task_key") or "trace").lower().replace("-", "_")
    out_path = runs_dir / f"{ts}_{key}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(result["report"])
    print("\n--- TRACE SUMMARY ---")
    print("Saved:", out_path)
    print("Stop reason:", result["stop_reason"], "| Drafts:", result["drafts"])
    print("LLM calls:", result["llm_calls"], "| Tokens:", result["tokens"], "| Sec:", result["elapsed_seconds"])


if __name__ == "__main__":
    main()
