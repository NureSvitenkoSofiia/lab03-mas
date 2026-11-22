"""Порівняння Coordinator (mode='single_turn') проти Workflow: 3 задачі x 3 повтори (крок 12)."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner, RunConfig
from google.genai import types

load_dotenv()

from app.agent import build_workflow, gemini
from app.coordinator import build_coordinator


async def measure(agent, prompt: str, app_name: str, is_coord: bool = False) -> dict:
    for attempt in range(4):
        try:
            runner = InMemoryRunner(agent=agent, app_name=app_name)
            session = await runner.session_service.create_session(app_name=app_name, user_id="cmp")
            msg = types.Content(role="user", parts=[types.Part(text=prompt)])

            calls = 0
            tokens = 0
            authors = []
            t0 = time.perf_counter()
            cfg = RunConfig(max_llm_calls=18) if is_coord else RunConfig()

            async def _collect():
                nonlocal calls, tokens
                async for event in runner.run_async(
                    user_id="cmp", session_id=session.id, new_message=msg, run_config=cfg
                ):
                    if event.usage_metadata:
                        calls += 1
                        tokens += event.usage_metadata.total_token_count or 0
                        authors.append(event.author)

            try:
                await asyncio.wait_for(_collect(), timeout=75)
                stop = "done"
            except TimeoutError:
                stop = "timeout_75s"

            sec = round(time.perf_counter() - t0, 2)
            sess = await runner.session_service.get_session(
                app_name=app_name, user_id="cmp", session_id=session.id
            )
            return {
                "calls": calls,
                "tokens": tokens,
                "seconds": sec,
                "authors": authors,
                "stop_reason": sess.state.get("stop_reason", stop),
            }
        except KeyError:
            raise
        except Exception as exc:
            if attempt == 3 or ("429" in str(exc) and "PerDay" in str(exc)):
                raise
            print(f"  [retry {attempt+1}] {exc}", flush=True)
            await asyncio.sleep(4)
    raise RuntimeError("unreachable")


async def main() -> None:
    reqs = json.loads(Path("eval/requests.json").read_text(encoding="utf-8"))
    selected = [r for r in reqs if r["id"] in {"JL-24", "JL-27", "JL-31"}]

    out_path = Path("eval/coordinator_results.json")
    rows = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else []
    done_keys = {(x["id"], x["repeat"]) for x in rows}
    lock = asyncio.Lock()
    sem = asyncio.Semaphore(2)

    async def run_pair(r: dict, rep: int) -> None:
        async with sem:
            print(f"=== START {r['id']} rep {rep} ===", flush=True)
            coord = build_coordinator(gemini())
            c_res = await measure(coord, r["prompt"], f"coord_{r['id']}_{rep}", is_coord=True)
            wf = build_workflow(gemini(), use_kb_agent=False)
            w_res = await measure(wf, r["prompt"], f"wf_{r['id']}_{rep}", is_coord=False)
            print(
                f"=== DONE {r['id']} rep {rep} | Coord: {c_res['calls']} calls, {c_res['tokens']} tok, {c_res['seconds']}s ({c_res['stop_reason']}) "
                f"| WF: {w_res['calls']} calls, {w_res['tokens']} tok, {w_res['seconds']}s ({w_res['stop_reason']}) ===",
                flush=True,
            )
            async with lock:
                rows.append({"id": r["id"], "repeat": rep, "coordinator": c_res, "workflow": w_res})
                rows.sort(key=lambda x: (x["id"], x["repeat"]))
                out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    tasks = [run_pair(r, rep) for r in selected for rep in range(1, 4) if (r["id"], rep) not in done_keys]
    await asyncio.gather(*tasks)
    print("Saved all eval/coordinator_results.json", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
