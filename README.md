# HW4: RAG + MCP Knowledge Base — Market Manipulation

База знаний по рыночным манипуляциям (definition + detection), индексация в Chroma, поиск через **MCP** (`chroma-mcp`) и агент **LangChain + GigaChat**.

**Репозиторий:** https://github.com/kirill-nekurim/MCP_Manipulative_Trading

## Соответствие критериям ДЗ

| Критерий (вес) | Где в репозитории |
|----------------|-------------------|
| Корпус, чанки, метаданные, индекс (20%) | `docs/`, `ingest.py` |
| MCP-сервер, инструмент поиска (20%) | `chroma-mcp`, инструмент **`chroma_query_documents`**, `mcp_search_demo.py` |
| Агент LangChain + MCP (20%) | `agent_demo.py` (GigaChat + `langchain-mcp-adapters`) |
| top-k с document_id, chunk_id, source (15%) | вывод `mcp_search_demo.py` / `agent_demo.py` |
| Eval 15–20 запросов + оценка (15%) | `eval_queries.csv`, `eval_report.md`, `run_eval.py` |
| Воспроизводимый README (10%) | этот файл, шаги 1–7 ниже |

**MCP-инструмент поиска:** `chroma_query_documents` (коллекция `market_manipulation_kb`).

**Агент:** обёртка `search_knowledge_base` → внутри вызывает тот же MCP (GigaChat не принимает сложную JSON-схему chroma-mcp).

## Минимальный состав репозитория (для сдачи)

Обязательное по заданию — без лишних файлов:

```
README.md
requirements.txt
.env.example
mcp_config.example.json
ingest.py
search_demo.py
mcp_search_demo.py
agent_demo.py
mcp_chroma.py          # общий MCP-клиент для agent + eval
run_eval.py
eval_queries.csv
eval_report.md
docs/
```

Не коммитится: `.env`, `chroma_db/`, `mcp_config.json` (личные пути), `eval_results.csv` (генерируется).

## Структура проекта

```
hw4/
├── docs/                      # корпус (8 документов + overview)
├── docs/overview.md           # карта корпуса
├── ingest.py                  # разбиение по ## + индексация в Chroma
├── search_demo.py             # прямой поиск в Chroma (без MCP)
├── mcp_search_demo.py         # поиск через MCP chroma_query_documents
├── mcp_chroma.py              # общий клиент MCP для Chroma
├── agent_demo.py              # GigaChat-агент + MCP search
├── run_eval.py                # прогон eval_queries.csv
├── eval_queries.csv           # 18 тестовых запросов
├── eval_results.csv           # результаты (генерируется)
├── eval_report.md             # отчёт (генерируется)
├── mcp_config.json            # конфиг MCP для Cursor
├── mcp_config.example.json
├── requirements.txt
├── .env.example
└── chroma_db/                 # индекс (создаётся ingest.py, в .gitignore)
```

## Требования

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (рекомендуется) или pip
- `uvx` в PATH (для `chroma-mcp`)
- API-ключ GigaChat ([developers.sber.ru](https://developers.sber.ru/studio/))

## Установка

```bash
cd hw4
python3.11 -m venv .venv
source .venv/bin/activate

uv pip install -r requirements.txt
# или: pip install -r requirements.txt
```

## Переменные окружения

```bash
cp .env.example .env
```

Заполните `.env`:

| Переменная | Описание |
|------------|----------|
| `GIGACHAT_CREDENTIALS` | Authorization key (base64) |
| `GIGACHAT_SCOPE` | `GIGACHAT_API_PERS` для личного пространства |
| `GIGACHAT_MODEL` | например `GigaChat-2` |
| `GIGACHAT_VERIFY_SSL_CERTS` | `false` для локальной разработки без CA |

**Не коммитьте `.env`** — файл в `.gitignore`.

## 1. Индексация корпуса

```bash
python ingest.py --reset
```

- Читает все `.md` из `docs/`
- Режет по заголовкам `##`
- Метаданные: `document_id`, `chunk_id`, `source`, `section`, `chunk_index`, …
- Сохраняет в коллекцию `market_manipulation_kb` → `./chroma_db`
- Ожидаемо: **100 чанков**

При изменении документов перезапустите с `--reset`.

## 2. Поиск без MCP (проверка индекса)

```bash
python search_demo.py --query "What is spoofing?" --k 3
```

## 3. MCP-сервер

Используется официальный **[chroma-mcp](https://github.com/chroma-core/chroma-mcp)**.

**Инструмент поиска:** `chroma_query_documents`

Параметры:
- `collection_name`: `market_manipulation_kb`
- `query_texts`: `["..."]`
- `n_results`: `k`

### Ручной вызов MCP

```bash
python mcp_search_demo.py --query "What is spoofing?" --k 3
```

### Cursor

Добавьте в `~/.cursor/mcp.json` (см. `mcp_config.example.json`):

```json
"knowledge_base": {
  "command": "uvx",
  "args": [
    "chroma-mcp",
    "--client-type", "persistent",
    "--data-dir", "/ABSOLUTE/PATH/TO/hw4/chroma_db"
  ]
}
```

## 4. Агент (GigaChat + MCP)

```bash
python agent_demo.py --query "What is spoofing in financial markets?" --k 3
```

Цепочка:

```
User → GigaChat agent → search_knowledge_base → MCP chroma_query_documents → Chroma
```

> **Замечание:** GigaChat не принимает сложную JSON-схему MCP-инструмента (`anyOf`).  
> Агент использует обёртку `search_knowledge_base`, которая вызывает MCP внутри.  
> Запрос в Chroma берётся из CLI (английский), т.к. embedding `all-MiniLM-L6-v2` лучше работает на English.

## 5. Оценка качества (eval)

18 запросов в `eval_queries.csv` (точные, широкие, негативные, multi-source, metadata).

```bash
python run_eval.py
```

Создаёт:
- `eval_results.csv` — полные результаты
- `eval_report.md` — сводная таблица

Поля: `query`, `expected_document_id`, `first_hit`, `in_top3`, `manual_judgement`, `comment`.

При необходимости отредактируйте `manual_judgement` и `comment` вручную в CSV.

## MCP-инструменты (chroma-mcp)

| Инструмент | Назначение |
|------------|------------|
| `chroma_query_documents` | **семантический поиск** (основной для ДЗ) |
| `chroma_list_collections` | список коллекций |
| `chroma_get_collection_count` | число документов |

## Критерии ДЗ (чеклист)

- [x] Корпус 5–10 документов с метаданными
- [x] `ingest.py` — чанки + индексация
- [x] MCP `chroma-mcp` + `mcp_config.json`
- [x] `mcp_search_demo.py` — демо MCP-поиска
- [x] `agent_demo.py` — LangChain + GigaChat + MCP
- [x] top-k с `document_id`, `chunk_id`, `source`, score
- [x] eval 15–20 запросов + отчёт
- [x] README с инструкцией запуска

## Известные ограничения

1. **Embeddings:** Chroma default `all-MiniLM-L6-v2` — запросы лучше формулировать на **английском**.
2. **GigaChat + MCP schema:** прямой bind `chroma_query_documents` падает с `IncorrectSchemaException` — используется обёртка `search_knowledge_base`.
3. **Первый запуск:** Chroma скачивает ONNX-модель (~79 MB) в `~/.cache/chroma/` — при обрыве SSL повторите команду.

## Автор / тема

Корпус: market manipulation (Pump and Dump, Spoofing, Wash Trading, Marking the Close) — definitions + detection methods.
