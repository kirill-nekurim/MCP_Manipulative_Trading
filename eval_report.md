# Evaluation Report — Market Manipulation KB

Search: MCP tool `chroma_query_documents`, top-k=3, queries in English (Chroma embedding: all-MiniLM-L6-v2).

**Summary:** 16/18 queries with expected hit in top-3 (`in_top3=yes`).

Review `manual_judgement` and `comment` in `eval_results.csv` (генерируется `python run_eval.py`).

**Ограничения (честная оценка):** embedding Chroma `all-MiniLM-L6-v2` лучше на английских запросах; overview-документ (#4, #17) иногда не попадает в top-3 — см. комментарии в таблице.

| # | Type | Query | Expected | First hit | Top-3 | In top-3 | Comment |
|---|------|-------|----------|-----------|-------|----------|---------|
| 1 | exact_fact | What is wash trading? | wash_trading | wash_trading/wash_trading_chunk_01 | yes | yes | expected doc in top-3: wash_trading |
| 2 | terminology | Define spoofing in financial markets | spoofing|spoofing_detection | spoofing/spoofing_chunk_01 | yes | yes | expected doc in top-3: spoofing, spoofing_detection |
| 3 | specific_document | How does a pump and dump scheme work step by step? | pump_and_dump|pump_and_dump_detection | pump_and_dump_detection/pump_and_dump_detection_chunk_01 | yes | yes | expected doc in top-3: pump_and_dump_detection |
| 4 | broad_semantic | What manipulation schemes are listed in the knowledge bas... | knowledge_base_overview | spoofing/spoofing_chunk_13 | no | no | expected {'knowledge_base_overview'}, got spoofing |
| 5 | negative | Who is the CEO of JPMorgan wash trading compliance team? | none | spoofing/spoofing_chunk_13 | yes | yes | low relevance score — good negative |
| 6 | multi_source | How do regulators detect spoofing? | spoofing_detection|spoofing | spoofing_detection/spoofing_detection_chunk_11 | yes | yes | expected doc in top-3: spoofing, spoofing_detection |
| 7 | metadata_source | Which document describes marking the close from CFA Insti... | marking_the_close | marking_the_close_detection/marking_the_close_detection_chunk_01 | yes | yes | expected doc in top-3: marking_the_close |
| 8 | detection_method | Wash trading detection indicators and patterns | wash_trading_detection | wash_trading_detection/wash_trading_detection_chunk_04 | yes | yes | expected doc in top-3: wash_trading_detection |
| 9 | exact_fact | Why do closing prices matter for marking the close? | marking_the_close|marking_the_close_detection | marking_the_close/marking_the_close_chunk_02 | yes | yes | expected doc in top-3: marking_the_close |
| 10 | negative | What are MiFID III position limits for carbon credits? | none | spoofing/spoofing_chunk_09 | yes | yes | low relevance score — good negative |
| 11 | terminology | What is layering in the order book related to spoofing? | spoofing | spoofing_detection/spoofing_detection_chunk_01 | yes | yes | expected doc in top-3: spoofing |
| 12 | specific_document | Pump and dump use of Telegram and social media | pump_and_dump | pump_and_dump_detection/pump_and_dump_detection_chunk_06 | yes | yes | expected doc in top-3: pump_and_dump |
| 13 | broad_semantic | Definition versus detection documents in the corpus | knowledge_base_overview | knowledge_base_overview/knowledge_base_overview_chunk_03 | yes | yes | expected doc in top-3: knowledge_base_overview |
| 14 | multi_source | Difference between wash trading definition and detection | wash_trading|wash_trading_detection | wash_trading/wash_trading_chunk_01 | yes | yes | expected doc in top-3: wash_trading, wash_trading_detection |
| 15 | detection_method | Spoofing surveillance patterns FINRA cross-market | spoofing_detection | spoofing_detection/spoofing_detection_chunk_04 | yes | yes | expected doc in top-3: spoofing_detection |
| 16 | negative | How to file personal income tax in Russia for traders? | none | pump_and_dump/pump_and_dump_chunk_08 | yes | yes | low relevance score — good negative |
| 17 | metadata_source | How many manipulation types and documents does knowledge_... | knowledge_base_overview | wash_trading/wash_trading_chunk_13 | no | no | expected {'knowledge_base_overview'}, got wash_trading |
| 18 | exact_fact | What happens in the dump phase of pump and dump? | pump_and_dump|pump_and_dump_detection | pump_and_dump_detection/pump_and_dump_detection_chunk_03 | yes | yes | expected doc in top-3: pump_and_dump_detection |

## How to reproduce

```bash
python ingest.py --reset
python run_eval.py
```

Results: `eval_results.csv`.
