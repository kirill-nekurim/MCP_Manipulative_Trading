# Market Manipulation Knowledge Base — Overview

**Document ID:** knowledge_base_overview
**Source:** project corpus index
**Document Type:** overview
**Language:** Russian
**Last Updated:** 2026-06-04

## Что это за система

Это специализированная база знаний (knowledge base) по **рыночным манипуляциям на финансовых рынках**. 

Корпус предназначен для RAG-систем и ИИ-агентов, которые должны уметь:
- понимать природу различных схем манипуляций,
- различать их по характеристикам,
- знать регуляторные и технические подходы к их обнаружению.

База построена по принципу **"Definition + Detection"**:
- **Definition** документы объясняют, что такое манипуляция, как она работает и почему она illegal.
- **Detection** документы описывают, как эту манипуляцию выявляют регуляторы, биржи и системы trade surveillance.

Все документы имеют единообразную структуру метаданных в заголовке:
- `Document ID`
- `Source` (регуляторы: SEC, FINRA, CFA Institute, FCA, CFTC и др.)
- `URL`
- `Document Type` (`definition`, `detection_method`, `surveillance_detection`, `ethics_standard`)
- `Last Updated` / `Language`

## Какие типы манипуляций покрыты

| Тип манипуляции       | Definition | Detection | Краткое описание |
|-----------------------|------------|-----------|------------------|
| **Pump and Dump**     | ✅         | ✅        | Искусственное раздувание цены актива через misleading information с последующей массовой продажей (dump) |
| **Spoofing**          | ✅         | ✅        | Размещение крупных заявок без намерения их исполнять для создания ложного impression of supply/demand |
| **Wash Trading**      | ✅         | ✅        | Одновременная покупка и продажа одного и того же актива одним лицом/группой для создания видимости объёма и ликвидности |
| **Marking the Close** | ✅         | ✅        | Торговля в конце торговой сессии с целью исказить closing/settlement price |

**Итого:** 4 типа манипуляций, 8 документов.

## Как связаны definitions ↔ detection

Связь организована **попарно** по типу манипуляции:

```
definitions/pump_and_dump.md          ↔  detection_method/pump_and_dump_detection.md
definitions/spoofing.md               ↔  detection_method/spoofing_detection.md
definitions/marking_the_close.md      ↔  detection_method/marking_the_close_detection.md
definitions/wash_trading.md           ↔  detection_method/wash_trading_detection.md
```

**Логика связи:**
- **Definition** документ отвечает на вопросы: "Что это?", "Как работает?", "Какие характеристики?", "Почему это manipulation?"
- **Detection** документ отвечает на вопросы: "Как это детектить?", "Какие паттерны и индикаторы?", "Какие данные нужны surveillance-системе?", "С позиции каких регуляторов это рассматривается?"

Такой дизайн позволяет RAG-системе отвечать как на **теоретические**, так и на **практические** вопросы (например: "Что такое spoofing?" vs "Как регуляторы выявляют spoofing?").

## Как читать проект

1. **Начни с `overview.md`** (этот файл) — общее понимание структуры и покрытия.
2. **definitions/** — читай, когда нужно понять природу схемы.
3. **detection_method/** — читай, когда нужно понять, как схему ловят.
4. Каждый документ можно читать независимо, но для полной картины рекомендуется читать пару definition + detection вместе.

**Для RAG / агента:**
- Документы разбиты на смысловые чанки (по заголовкам `##`).
- Каждый чанк содержит стабильные идентификаторы (`document_id`, `chunk_id`) и метаданные источника.
- Это позволяет агенту возвращать не просто текст, а точные ссылки на источник (`document_id` + `chunk_id` + `source`).

**Примеры вопросов, на которые база должна хорошо отвечать:**
- Что такое Pump and Dump и как его распознать?
- Какие признаки spoofing'а видны в order book?
- Почему Wash Trading сложно детектить?
- Как Marking the Close влияет на settlement price?
- Какие регуляторы считают ту или иную практику market manipulation?