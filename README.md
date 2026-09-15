# NexDoc

A semantic preprocessing layer that transforms heterogeneous enterprise artifacts into a unified, relationship-aware representation for downstream AI systems.

## Problem

Generic pipelines reduce complex enterprise documents (PDFs, spreadsheets, forms, and diagrams) into plain text or raw layout chunks. This process systematically destroys structural semantics and internal relationships, rendering the data largely incomprehensible for downstream Large Language Models and retrieval systems.

## Solution

NexDoc introduces a structure-first processing layer. Instead of discarding layout, formula links, and process paths, NexDoc extracts these documents into a strongly-typed graph.
PDFs, Excel spreadsheets, and Diagrams are semantically extracted into a Unified Schema, their relationships resolved, and connected into a Semantic Graph, resulting in a completely AI-ready representation.

## Key Features

* Multi-format semantic extraction
* Document/PDF processing
* Spreadsheet semantic extraction
* Diagram understanding
* Unified semantic schema
* Relationship extraction
* Cross-artifact linking
* Semantic graph
* Confidence and provenance
* Human review
* Deterministic evaluation
* Evidence-backed retrieval

## Architecture

NexDoc uses format-specific adapters to interpret the syntax of different file types:
- **Documents (PyMuPDF):** Extracts structural paragraphs rather than arbitrary chunks.
- **Spreadsheets (Openpyxl):** Evaluates formula dependencies explicitly (e.g. `SUM(B3:B5)` forms a directed graph between output and inputs).
- **Diagrams (OpenCV + Tesseract):** Uses Hough transforms and contour detection to extract explicit process nodes and connecting arrows without the latency or hallucination of Vision-Language Models.

## Supported Artifacts

- PDF Documents (Native & Scanned)
- Excel Spreadsheets (.xlsx)
- Diagrams & Flowcharts (.png, .jpg)

## Semantic Representation

Data is mapped to a unified `Artifact` schema containing strongly typed `Regions` (e.g., `header`, `data`, `formula`, `process_node`). Each region maintains its precise visual bounding box and original data type.

## Semantic Graph

Parsed regions form a directed semantic graph. Relationships are created between nodes: for instance, a formula output cell points to its input cells, or a flowchart decision node points to its subsequent steps.

## Cross-Artifact Relationships

NexDoc features a cross-artifact linker that stitches together disconnected documents. A vendor ID located in a scanned invoice PDF is semantically linked to the corresponding row in an Excel vendor master list, forming a continuous global enterprise graph.

## Confidence & Provenance

Every extracted region carries a `confidence` metric and an explicit `provenance` trace (e.g., source file, page, exact coordinate). When downstream AI leverages NexDoc, all answers can be mathematically traced back to the original source pixels.

## Benchmark

A controlled downstream retrieval/question-answering benchmark comparing flattened source representations against NexDoc's relationship-aware semantic representation. Note that this measures deterministic retrieval capability on structural questions, isolating the preprocessing effect. 

```text
Baseline (Flattened Text): 3/7 = 42.9%
NexDoc (Semantic Graph):   7/7 = 100.0%
Improvement: +57.1 percentage points
```

## Dataset

The benchmark is evaluated against a synthetic enterprise procurement sample:
* purchase order
* invoice
* budget
* vendor master
* approval flow

## Limitations

- Deterministic entity-resolution heuristics (requires further ML/embedding integration for synonyms).
- Difficulties parsing overlapping or complex diagram structures.
- Standard OCR limitations on heavily degraded documents.
- Current benchmark scope is limited to the included procurement dataset.

## Running Locally

To install and run the interactive NexDoc human-review UI and API layer:

```bash
pip install -r requirements.txt
python -m webapp.main
```
Navigate to `http://127.0.0.1:8000` to view the Semantic Graph.

## Testing

To run the unit tests:

```bash
pytest
```

## Evaluation

To run the deterministic fact-recoverability benchmark:

```bash
python eval/benchmark.py
```

To test the retrieval-bounded Optional Groq QA (ensure `.env` has `GROQ_API_KEY` set):

```bash
python scripts/test_qa.py
```

## Project Structure

```text
NexDoc/
├── adapters/             # Format-specific parsers
├── dataset/              # Procurement sample dataset
├── docs/                 # Architecture and evaluation details
├── eval/                 # Deterministic benchmarks
├── out/                  # Generated demo files
├── qa/                   # Retrieval-first Groq Q&A
├── reports/              # Benchmark output JSON
├── scripts/              # Dataset and test execution scripts
├── tests/                # Pytest suites and fixtures
├── webapp/               # FastAPI backend and UI
├── .env.example          # Template for API keys
├── .gitignore
├── README.md
├── requirements.txt
└── run_adapter.py        # CLI interface for direct processing
```
