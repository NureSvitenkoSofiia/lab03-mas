# Паспорт мультиагентної системи: jarlight-feature-sdlc

## 1. Ідентифікація
- **Назва:** `jarlight-feature-sdlc`
- **Версія:** `1.0.0`
- **Дата:** `22.11.2026`
- **Автор:** Світенко Софія Миколаївна, група ПЗПІ-23-3, e-mail: `sofiia.svitenko@nure.ua`
- **Ліцензія:** MIT
- **Репозиторій GitHub:** https://github.com/NureSvitenkoSofiia/lab03-mas
- **Посилання на архів:** https://drive.google.com/drive/folders/1bWwv-3Tem3rG6mSIj-EJxgJ3uIas73Yg

## 2. Призначення
- **Задача:** Автоматизація етапу проєктування та конструювання ігрових фіч і механік 2D-головоломки **JarLight** на рушії Unity (C# ECS / Burst, гексагональна сітка, оптичні закони Снелла й RGB, нормативи `Par Moves`) — від текстового GDD-запиту до перевіреного пакета змін (Draft Feature PR, JSON-пресет рівня, NUnit-тести).
- **Зв'язок із кваліфікаційною роботою:** Тема КР здобувачки: *«Розробка ігрового застосунку в жанрі логічної головоломки «JarLight» на платформі Unity»* (інтеграція з базою знань ЛР 2 `jarlight-kb` та заділ під робоче місце ЛР 4).
- **Вхід і результат:** Вхід — текстова задача з беклогу (`JL-XX ...`); результат — звіт Draft Feature PR у Markdown із оцінкою готовності, планом ECS-змін, фрагментом C# коду, JSON-пресетом рівня та Unity Test Framework (`NUnit`) тестами, або перелік уточнювальних запитань (`needs_clarification`).
- **Межі:** Не змінює файли Unity-проєкту на диску безпосередньо, не запускає компілятор C# чи Unity Editor, не використовує зовнішній інтернет поза Gemini API та локальною ChromaDB (`jarlight_kb`).
- **Чому кілька агентів, а не один:** Побудова фічі в Unity ECS вимагає різних компетенцій: аналізу повноти GDD, проєктування Burst-безпечного C#-коду й NUnit-тестів, а також незалежної критики оптики/балансу й продуктивності ECS. Окремі ролі зі строгими `output_schema`, детермінований лінт і паралельні рецензенти з `JoinNode` унеможливлюють ситуацію, коли одна модель ігнорує власні помилки або вигадує код на нечіткий запит.

## 3. Агенти і вузли
| Вузол | Тип (LLM / функція / Join) | Роль | Вихідна схема | Ключ стану |
| :--- | :--- | :--- | :--- | :--- |
| `intake_task` | функція | Валідація опису задачі та виділення `JL-XX` | `Event(route="ok"/"reject")` | `request`, `task_key`, `drafts` |
| `kb_researcher` / `retrieve_context` | LLM (`tools`) / функція | Пошук правил оптики та ECS у `jarlight_kb` (ЛР 2) | текст фрагментів `[[...]]` | `kb_context` |
| `feature_architect` | LLM | Оцінка готовності GDD та план змін | `FeaturePlanSpec` | `plan` |
| `readiness_gate` | функція | Рання зупинка неповних вимог | `Event(route="ok"/"clarify")` | `stop_reason` |
| `unity_implementer` | LLM | Генерація C# ECS, JSON-пресету і NUnit тестів | `UnityFeatureBundle` | `implementation` |
| `unity_policy_lint` | функція | Детермінований лінт Burst/ECS, JSON, тестів | `Event(route="ok"/"fix"/"max_reached")` | `drafts`, `lint_passed`, `lint_errors` |
| `game_balance_reviewer` | LLM | Рев'ю фізики світла, RGB і `Par Moves` | `GameBalanceReviewReport` | `balance_review` |
| `unity_ecs_qa_reviewer` | LLM | Рев'ю Burst-безпеки, `max_bounces` і NUnit | `UnityEcsQaReport` | `qa_review` |
| `reviews` | `JoinNode` | Бар'єр синхронізації двох паралельних рев'ю | очікування обох гілок | `—` |
| `pr_gate` | функція | Консолідація вердиктів та контроль циклу | `Event(route="revise"/"publish")` | `review_feedback`, `stop_reason` |
| `build_feature_pr` | функція | Збірка фінального Draft Feature PR зі стану | Markdown + JSON-об'єкт | `pr_draft`, `report` |

## 4. Граф
- **Шаблони:** лінійний конвеєр валідації -> паралельне розгалуження (fan-out/fan-in з `JoinNode`) -> обмежений цикл генератора і критика -> рання зупинка (`reject` / `clarify`).
- **Ліміти:** `MAX_ROUNDS = 3`; `max_concurrency = 2`; `MAX_CODE_LEN = 3800`.
- **Схема графа:** `docs/screenshots/workflow_graph.png` (`docs/workflow_graph.drawio`).

## 5. Середовище
- **Фреймворк:** `google-adk==2.15.0` (`Workflow`, `JoinNode`, `Agent`, `InMemoryRunner`); модель: `gemini-3-flash-preview` (перевірено також із `gemini-3.5-flash-lite` і `gemini-embedding-001` для `jarlight_kb`).
- **Запуск:** `agents-cli playground` або `PYTHONPATH=. uv run python run_cli.py "<запит>"`
- **Змінні оточення:** `GEMINI_API_KEY`, `GEMINI_MODEL`, `KB_VAULT_PATH`, `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION`, `KB_MAX_DISTANCE`.

## 6. Результати
- **Тести:** `15` пройдено з `15` (`uv run pytest -v` зі `ScriptedLlm`, без звернень до Gemini API).
- **Експеримент (5 запитів), середнє:** якість 0–2 команда `2.00` / один агент `0.80`; виклики моделі: команда `7.20` / один агент `1.00`; токени: `17 856.2` / `1 755.6`; час, с: `64.86` / `7.09`.
- **Порівняння Coordinator vs Workflow (3×3):** у завершених повних прогонах `Coordinator` витратив у середньому `13.0` викл. / `30 202.5` токенів (`119.14 с`), перериваючись у `7/9` запусків за лімітом `75 с` (`5.89` викл. / `11 391.0` ток. / `88.72 с` загалом); `Workflow` працював у середньому `73.38 с` (`7.56` викл. / `13 273.8` токенів).

## 7. Відомі обмеження та ризики
- На безкоштовному тарифі Gemini Developer API діють обмеження на кількість запитів на хвилину/добу (`429`/`503`), що знижується прапорцем `--no-kb-agent` та `HttpRetryOptions`.
- Згенеровані C# фрагменти, JSON-пресети та NUnit-тести потребують компіляції в Unity Editor перед злиттям у `main`.
- Із векторного пошуку `jarlight_kb` фільтруються чернетки з папки `Inbox/`, щоб неперевірені пропозиції не підміняли вимоги нових GDD-задач.

## 8. Журнал змін
- `1.0.0` (`22.11.2026`) — перша публікація мультиагентної системи `jarlight-feature-sdlc` (ЛР 3).
