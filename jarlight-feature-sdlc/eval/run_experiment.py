"""Порівняльний експеримент Workflow проти Solo Baseline на 5 задачах JarLight (крок 11)."""

from __future__ import annotations

import asyncio
import json
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

load_dotenv()

from app.agent import build_workflow, gemini
from app.baseline import build_solo_agent


async def run_one(agent, prompt: str, app_name: str) -> dict:
    for attempt in range(5):
        try:
            runner = InMemoryRunner(agent=agent, app_name=app_name)
            session = await runner.session_service.create_session(app_name=app_name, user_id="exp")
            msg = types.Content(role="user", parts=[types.Part(text=prompt)])

            calls = 0
            tokens = 0
            t0 = time.perf_counter()
            final_text = ""

            async for event in runner.run_async(user_id="exp", session_id=session.id, new_message=msg):
                if event.usage_metadata:
                    calls += 1
                    tokens += event.usage_metadata.total_token_count or 0
                if event.content and event.content.parts:
                    txt = "".join(p.text or "" for p in event.content.parts)
                    if txt:
                        final_text = txt

            elapsed = round(time.perf_counter() - t0, 2)
            sess = await runner.session_service.get_session(
                app_name=app_name, user_id="exp", session_id=session.id
            )
            state = dict(sess.state)
            return {
                "calls": calls,
                "tokens": tokens,
                "seconds": elapsed,
                "drafts": state.get("drafts", 1),
                "stop_reason": state.get("stop_reason", "solo"),
                "report": state.get("report") or final_text,
                "solo_result": state.get("solo_result"),
            }
        except Exception as exc:
            if attempt == 4:
                raise
            print(f"  [retry {attempt+1}] {exc}")
            await asyncio.sleep(8)
    raise RuntimeError("unreachable")


async def main() -> None:
    requests = json.loads(Path("eval/requests.json").read_text(encoding="utf-8"))
    existing = {r["id"]: r for r in json.loads(Path("eval/results.json").read_text(encoding="utf-8"))} if Path("eval/results.json").exists() else {}
    existing_blind = {b["task"]: b for b in json.loads(Path("eval/blind_pairs.json").read_text(encoding="utf-8"))} if Path("eval/blind_pairs.json").exists() else {}
    results = []
    blind_items = []
    rng = random.Random(42)

    for item in requests:
        if item["id"] in existing and item["id"] in existing_blind:
            results.append(existing[item["id"]])
            blind_items.append(existing_blind[item["id"]])
            print(f"=== Skipping already saved {item['id']} ===")
            continue
        tid = item["id"]
        prompt = item["prompt"]
        print(f"=== Running {tid} ===", flush=True)

        wf = build_workflow(gemini(), use_kb_agent=False)
        wf_res = await run_one(wf, prompt, f"wf_{tid}")
        print(f"  Workflow -> calls={wf_res['calls']}, tokens={wf_res['tokens']}, sec={wf_res['seconds']}, drafts={wf_res['drafts']}, stop={wf_res['stop_reason']}", flush=True)

        await asyncio.sleep(1.5)
        solo = build_solo_agent(gemini())
        solo_res = await run_one(solo, prompt, f"solo_{tid}")
        print(f"  Solo     -> calls={solo_res['calls']}, tokens={solo_res['tokens']}, sec={solo_res['seconds']}", flush=True)

        results.append(
            {
                "id": tid,
                "category": item["category"],
                "prompt": prompt,
                "workflow": {
                    "calls": wf_res["calls"],
                    "tokens": wf_res["tokens"],
                    "seconds": wf_res["seconds"],
                    "drafts": wf_res["drafts"],
                    "stop_reason": wf_res["stop_reason"],
                    "report": wf_res["report"],
                },
                "solo": {
                    "calls": solo_res["calls"],
                    "tokens": solo_res["tokens"],
                    "seconds": solo_res["seconds"],
                    "drafts": 1,
                    "solo_result": solo_res["solo_result"],
                    "report": solo_res["report"],
                },
            }
        )

        pair = [
            {"id": tid, "system": "workflow", "text": wf_res["report"]},
            {"id": tid, "system": "solo", "text": json.dumps(solo_res["solo_result"], ensure_ascii=False, indent=2) if solo_res["solo_result"] else solo_res["report"]},
        ]
        rng.shuffle(pair)
        blind_items.append({"task": tid, "A": pair[0], "B": pair[1]})
        Path("eval/results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        Path("eval/blind_pairs.json").write_text(json.dumps(blind_items, ensure_ascii=False, indent=2), encoding="utf-8")
        await asyncio.sleep(1.5)

    print("Saved eval/results.json and eval/blind_pairs.json")


if __name__ == "__main__":
    asyncio.run(main())
