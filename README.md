# Market Manipulation Knowledge Base (RAG + MCP)

База знаний по рыночным манипуляциям: корпус markdown → Chroma → поиск через **MCP** (`chroma-mcp`) → агент **LangChain + GigaChat**.

**Репозиторий:** https://github.com/kirill-nekurim/MCP_Manipulative_Trading

**После клона:** `pip install -r requirements.txt` → `python src/ingest.py --reset` → команды из раздела [«Для проверяющего»](#для-проверяющего-воспроизведение) ниже. Для агента — `.env` по `.env.example` (нужен `GIGACHAT_CREDENTIALS`).

## Структура

```
MCP_Manipulative_Trading/
├── README.md
├── requirements.txt
├── .env.example
├── mcp_config.example.json
├── docs/                    # корпус (8 документов + overview)
├── eval/
│   ├── queries.csv          # 18 тестовых запросов
│   └── report.md            # отчёт по качеству поиска
├── src/
│   ├── config.py            # пути и константы
│   ├── ingest.py            # индексация
│   ├── search_demo.py       # поиск в Chroma (без MCP)
│   ├── mcp_search_demo.py     # поиск через MCP
│   ├── mcp_chroma.py        # MCP-клиент
│   ├── agent_demo.py        # GigaChat-агент
│   └── run_eval.py          # прогон eval
└── chroma_db/               # индекс (генерируется, не в git)
```

## Критерии ДЗ

| Критерий | Реализация |
|----------|------------|
| Корпус, чанки, метаданные (20%) | `docs/`, `src/ingest.py` |
| MCP-сервер (20%) | `chroma-mcp`, инструмент **`chroma_query_documents`** |
| Агент LangChain + MCP (20%) | `src/agent_demo.py` |
| top-k + metadata (15%) | вывод `mcp_search_demo` / `agent_demo` |
| Eval 15–20 запросов (15%) | `eval/queries.csv`, `eval/report.md` |
| README (10%) | этот файл |

**MCP-инструмент:** `chroma_query_documents` · коллекция `market_manipulation_kb`

## Для проверяющего (воспроизведение)

```bash
pip install -r requirements.txt
python src/ingest.py --reset
python src/mcp_search_demo.py -q "What is spoofing?" --k 3
python src/run_eval.py                    # eval уже в eval/report.md
cp .env.example .env                      # только для agent_demo
python src/agent_demo.py -q "What is spoofing?" --k 3
```

| Шаг | Команда / файл |
|-----|----------------|
| Корпус | уже в `docs/` (8 документов + `overview.md`) |
| Индексация | `python src/ingest.py --reset` → `chroma_db/`, ~100 чанков |
| Поиск через **MCP** | `python src/mcp_search_demo.py -q "What is spoofing?" --k 3` |
| Агент LangChain + MCP + GigaChat | `.env` из `.env.example` → `python src/agent_demo.py -q "..." --k 3` |
| Eval (18 запросов) | `python src/run_eval.py` → `eval/report.md` |

**MCP:** отдельный сервер не нужен — при вызове скриптов поднимается `uvx chroma-mcp` (stdio), инструмент **`chroma_query_documents`**.

**Агент:** `search_knowledge_base` (обёртка для GigaChat) → внутри тот же MCP `chroma_query_documents`. Запрос в Chroma берётся из CLI (не из перевода LLM).

**Пример полей в выводе поиска:**

```
document_id=spoofing, chunk_id=spoofing_chunk_01, score=0.84
source=docs/definitions/spoofing.md
```

**Eval (уже прогнан):** `eval/report.md` — **16/18** запросов: ожидаемый `document_id` в top-3. Промахи: #4, #17 (broad/metadata на `knowledge_base_overview`). Пересчёт: `python src/run_eval.py`.

**Агент:** в stdout — блок retrieved chunks (с `document_id` / `chunk_id`) и ответ GigaChat на основе контекста.

Зависимости: Python 3.11+, `pip install -r requirements.txt`, для MCP — `uv` (`uvx chroma-mcp`). Для шага «агент» — `GIGACHAT_CREDENTIALS` в `.env` (см. `.env.example`).

## 1. Индексация

Корпус лежит в `docs/` — скачивать ничего не нужно.

```bash
python src/ingest.py --reset
```

Чанки по `##`, метаданные: `document_id`, `chunk_id`, `source`, `section` → коллекция `market_manipulation_kb`.

## 2. Поиск (Chroma, без MCP)

```bash
python src/search_demo.py -q "What is wash trading?" --k 3
```

## 3. MCP

Сервер: [chroma-mcp](https://github.com/chroma-core/chroma-mcp). Запускается автоматически через `uvx` при `mcp_search_demo` / `agent_demo` / `run_eval`.

```bash
python src/mcp_search_demo.py -q "What is spoofing?" --k 3
```

Конфиг для Cursor (опционально): `mcp_config.example.json` → `data-dir` = абсолютный путь к `chroma_db`.

## 4. Агент GigaChat

```bash
python src/agent_demo.py -q "What is spoofing in financial markets?" --k 3
```

Цепочка: `search_knowledge_base` → MCP `chroma_query_documents` → Chroma.

> GigaChat не принимает сложную JSON-схему chroma-mcp; запрос в Chroma фиксируется из CLI (English embeddings).

## 5. Eval

```bash
python src/run_eval.py
```

- Вход: `eval/queries.csv`
- Выход: `eval/report.md`, `eval/results.csv` (генерируется, в `.gitignore`)

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `GIGACHAT_CREDENTIALS` | Authorization key ([developers.sber.ru](https://developers.sber.ru/studio/)) |
| `GIGACHAT_SCOPE` | `GIGACHAT_API_PERS` (личный аккаунт) |
| `GIGACHAT_MODEL` | например `GigaChat-2` |
| `GIGACHAT_VERIFY_SSL_CERTS` | `false` для локальной разработки |

## Ограничения

- Embedding Chroma: `all-MiniLM-L6-v2` — **запросы на английском** работают лучше.
- `chroma_db/` не в репозитории — пересоздаётся через `ingest.py`.

## Корпус

4 схемы × (definition + detection): Pump and Dump, Spoofing, Wash Trading, Marking the Close. См. `docs/overview.md`.
