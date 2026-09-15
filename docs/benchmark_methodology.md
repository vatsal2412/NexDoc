# NexDoc Benchmark Methodology

## Overview
This document defines the methodology used for the `baseline-vs-NexDoc` evaluation. The primary goal of this benchmark is to rigorously prove that the **structural relationships** extracted by NexDoc allow answering queries that are impossible for standard flattened text retrieval (Baseline A).

## Dataset
The dataset is the **Enterprise Procurement Package**, a multi-artifact synthetic dataset designed to replicate real-world enterprise procurement complexities.
- **Total Artifacts**: 5
  - `purchase_order.pdf` (Born-digital PDF)
  - `invoice.pdf` (Born-digital PDF)
  - `budget.xlsx` (Spreadsheet)
  - `vendor_master.xlsx` (Spreadsheet)
  - `approval_flow.png` (Diagram)

## Questions and Ground Truth Methodology
- **Total Questions**: 7
- **Categories**: Fact, Table, Relationship, Cross-artifact, Diagram, Multi-hop, and Distractor.
- **Ground Truth Isolation**: The `expected_answer` for each question is **strictly isolated**. It is NEVER injected into the retrieval context and the scripts contain self-validating integrity checks that immediately fail if the expected answer is found inside the retrieval logic execution context.

## Baseline A Representation
The baseline represents standard naive RAG pipelines that ingest PDFs, Excel files, and Images as unstructured plaintext. 
- **Method**: All files are parsed into flat text (e.g., CSV string for spreadsheets, raw text for PDFs).
- **Retrieval**: The entire flattened text corpus is evaluated to see if standard keyword density and textual proximity could surface the correct answer.

## NexDoc Representation
NexDoc uses the **Semantic Graph** representation.
- **Method**: Files are routed to domain-specific adapters (`spreadsheet`, `diagram`, `document`). The outputs are converted to a unified `Artifact` schema.
- **Cross-Artifact Linking**: A deterministic heuristic (`adapters/cross_artifact.py`) discovers edges between these artifacts (e.g., `vendor_master.xlsx` matching `Vendor ID V102` in `invoice.pdf`).
- **Retrieval**: The structured nodes and edges are provided to the evaluation engine.

## Scoring Methodology
A deterministic mock LLM scoring function is used to ensure reproducible metrics without API cost variance:
1. **Fact Checking**: Does the expected answer exist in the retrieved context?
2. **Structural Verification**: For complex questions (Cross-artifact, Multi-hop, etc.), does the context contain the explicit structural linkages required to make that hop? Baseline A is explicitly penalized for multi-hop queries because random word proximity does not equal logical structure.

## Limitations and Assumptions
- **Heuristic Edges**: The current `cross_artifact.py` relies on simplified heuristics (Regex for `\bV\d+\b` or `$ Amounts`) which would require a stronger semantic vector search for a universal production system.
- **Deterministic Evaluation**: Real LLM RAG pipelines may occasionally "hallucinate" correctly on Baseline A text, or fail to parse the Semantic Graph correctly. This deterministic evaluation assumes a perfect reasoning engine to measure pure *representation quality*.
