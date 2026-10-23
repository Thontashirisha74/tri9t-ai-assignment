## Decision Log — CardioTrack CT-200

## Decision 1: PDF Parsing and Hierarchy

**Prompt used:** How should a PDF manual be converted into a hierarchical section tree while preserving nested headings, body text, and duplicate heading titles?

**Decision:** Use `pypdf` for text extraction and custom parsing rules to identify section headings and establish parent-child relationships.

**Reasoning:** This provides a lightweight implementation without requiring an external document-processing service.

**Trade-off:** Irregular PDF formatting can make heading detection imperfect, so the parser needs targeted tests.

## Decision 2: Versioning and Content Comparison

**Prompt used:** How can two manual versions be compared without overwriting historical content?

**Decision:** Store each version separately in SQLite and use stable logical identifiers and content hashes to match and compare section nodes.

**Reasoning:** Separate versions preserve history and allow generated results to reference the exact source version.

**Trade-off:** Changes to section numbering or parent relationships may complicate logical matching.

## Decision 3: Test Generation and Staleness

**Prompt used:** How should generated test cases remain traceable to their source sections, and how can outdated results be identified?

**Decision:** Store source node IDs, version IDs, version numbers, and content hashes with each generation. Recheck the source section against the latest version when retrieving a generation.

**Reasoning:** This supports traceability and makes changes to source requirements visible.

**Trade-off:** The current generator is a development mock, not a real LLM. A production system needs a real provider integration, robust output validation, and additional automated tests.