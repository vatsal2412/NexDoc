# NexDoc Architecture & Design

NexDoc is a semantic preprocessing layer designed to transform heterogeneous enterprise artifacts (spreadsheets, documents, diagrams) into a unified, relationship-aware representation for downstream AI systems.

## Semantic Preprocessing Design

Generic pipelines reduce complex enterprise documents into plain text, discarding structural semantics and relationships. NexDoc instead extracts these artifacts into a **Unified Semantic Schema** that preserves the original meaning, spatial relationships, and provenance. 

### Unified Semantic Schema
All parsed artifacts are converted into a standard `Artifact` schema containing `Regions` (nodes) and `Relationships` (edges). Every extracted fact is strongly typed (e.g., `header`, `data`, `formula`, `table`, `process_node`) and maintains a precise coordinate/shape bounding box.

## Artifact Processing Adapters

### Document / PDF Processing
Extracts textual blocks from digital-born or scanned PDFs using PyMuPDF. Text is chunked into logical semantic regions rather than arbitrary character limits, preserving paragraph and structural boundaries.

### Spreadsheet Processing
**Trade-off:** `openpyxl` was chosen over `pandas` (ADR 0001). While `pandas` is standard for dataframes, it flattens sheets into 2D arrays, destroying cell coordinates, formulas, and visual layout. `openpyxl` allows NexDoc to extract explicit formula references (e.g., `SUM(B3:B5)`), creating direct semantic relationships between the output cell and its inputs.

### Diagram / OCR Processing
**Trade-off:** OpenCV + Tesseract OCR was chosen over Vision-Language Models (VLMs) (ADR 0002). VLMs hallucinate and fail to produce deterministic, programmatic graphs. Our approach uses OpenCV Hough transforms to detect flowchart shapes and arrows, coupled with OCR to read text inside the shapes, directly generating a graph of processes and decisions.

## Semantic Graph & Cross-Artifact Relationships

Once individual artifacts are parsed into regions, NexDoc connects them into a global **Semantic Graph**. 
- **Internal Relationships:** Spreadsheets link formula outputs to inputs; diagrams link process nodes via arrows.
- **Cross-Artifact Relationships:** A heuristic cross-artifact linker uses regex and entity matching to find relationships between separate documents. For example, a Vendor ID (`V102`) found in an Invoice PDF is linked to the corresponding row in a Vendor Master spreadsheet.

## Confidence & Provenance

Every extracted region carries a `confidence` score (e.g., OCR confidence or structural certainty) and explicit `provenance` (which file, page, and exact bounding box or cell coordinate it originated from). This guarantees that downstream AI answers can be traced back to the exact source pixel or cell.

## Evaluation Methodology

### Baseline vs NexDoc
The benchmark evaluates the **downstream structural recoverability** of facts.
- **Baseline:** The source artifacts are aggressively flattened into plain text / CSVs (mimicking naive RAG pipelines).
- **NexDoc:** The source artifacts are processed into the Semantic Graph, and a subset of context is retrieved using a bounded, relationship-aware retrieval algorithm.

### Deterministic Metric
**Trade-off:** Fact-recoverability (deterministic matching) was chosen over LLM-as-a-judge (ADR 0004). The benchmark explicitly checks whether the system can retrieve the necessary facts for a set of carefully authored Q&A pairs. This eliminates LLM grading variance and strictly tests the preprocessing pipeline's information retention.

## Known Limitations

- **Deterministic Cross-Artifact Resolution:** The cross-artifact linker relies on heuristic regex and exact string matching. It cannot yet resolve semantic synonyms (e.g., "Tech Corp" vs "Technology Corporation") without LLM assistance.
- **Complex Diagrams:** Highly overlapping or non-standard diagram shapes can confuse the OpenCV contour detection.
- **OCR Limitations:** Poorly scanned documents may produce low-confidence OCR text, breaking keyword-based retrieval.
- **Benchmark Scope:** The current deterministic benchmark is scoped to a 5-document procurement dataset. A much larger dataset is needed for comprehensive production readiness.
