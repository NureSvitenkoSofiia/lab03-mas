# jarlight-feature-sdlc

Мультиагентна система проєктування та конструювання ігрових фіч і механік для 2D-головоломки **JarLight** (Unity ECS / Burst, гексагональна сітка, оптичні закони Снелла, спектр RGB, `Par Moves`).

## Швидкий старт

```bash
uv sync --dev
cp .env.example .env   # заповніть GEMINI_API_KEY та шляхи до jarlight-kb
uv run pytest -v       # 15 офлайн-тестів зі ScriptedLlm (без API)
PYTHONPATH=. uv run python run_cli.py "JL-24: Додати PrismSplitter..."
```

## Склад системи
- `app/schemas.py` — Pydantic-контракти (`FeaturePlanSpec`, `UnityFeatureBundle`, `GameBalanceReviewReport`, `UnityEcsQaReport`, `SoloFeatureResult`).
- `app/agents.py` — 4 спеціалізовані LLM-агенти (`feature_architect`, `unity_implementer`, `game_balance_reviewer`, `unity_ecs_qa_reviewer`).
- `app/nodes.py` — детерміновані гейти та валідатор Burst/ECS/JSON/NUnit (`MAX_ROUNDS = 3`).
- `app/kb_connector.py` — інтеграція з базою знань `jarlight_kb` ЛР 2 (`kb_researcher` і `retrieve_context`).
- `app/agent.py` — граф `Workflow` з `JoinNode(name="reviews")` і `max_concurrency=2`.
- `app/baseline.py`, `app/coordinator.py` — одиночний агент і координатор `mode="single_turn"`.
