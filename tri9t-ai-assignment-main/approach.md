Implementation Approach — CardioTrack CT-200

1. Objective

Build a backend API to ingest, structure, version, browse, and compare CT-200 manual PDFs, and to generate traceable test cases from version-pinned section selections.

2. PDF Ingestion and Structure

The parser uses `pypdf` to extract text from each manual. It identifies section headings, builds a hierarchy, and records section numbers, heading levels, body text, page information, and content hashes.

Each section is represented as a node. Parent-child relationships preserve the manual hierarchy. When an intermediate heading is missing, a deep heading is attached to the nearest existing ancestor. Identical heading titles in different locations remain separate nodes.

3. Versioning and Change Detection

Each ingested manual is stored as a separate document version in SQLite. Section nodes are matched across versions using a logical identifier based on section number, normalized heading, and parent identity.

Content hashes are used to identify changed content. The comparison reports added, changed, removed, and unchanged sections. Previous versions are preserved instead of being overwritten.

4. API Design

FastAPI exposes endpoints for health checks, document and version listing, section browsing, node retrieval, text search, version comparisons, selections, test-case generation, and generated-result retrieval.

Pydantic models validate incoming selection data and generated test-case structure.

5. Version-Pinned Selections

Each selection stores section-node and document-version pairs. The API validates that a selected node belongs to the specified version. Duplicate node/version pairs within one selection are rejected.

6. Test-Case Generation

The current implementation uses a development mock generator. It produces three structured test cases containing titles, preconditions, steps, expected results, and source metadata. Battery values are extracted from the selected section's text to avoid mixing specifications between versions.

This mock implementation is not a real LLM integration. A production implementation should connect an LLM provider and validate its output before storing it.

7. Storage Decisions

- SQLite with SQLAlchemy stores documents, versions, section nodes, and selections.
- JSON storage in `generated/generations.json` stores generated test-case records.
- Content hashes and source metadata support traceability and staleness checks.

JSON was selected for generation records to keep the prototype simple. A larger deployment could move these records into relational tables or a dedicated document store.

8. Staleness and Impact Detection

When a generation is retrieved, its original source sections are compared with their corresponding logical sections in the latest document version. Changed or removed sections are reported in `stale_sources`, and the generation is marked stale.

9. Testing

Four automated parser tests currently pass. They cover missing intermediate headings, classification-list preservation, duplicate heading titles, and unique node IDs. API and generation behavior should also be covered with automated tests.

10. Known Limitations

- Generation currently uses mock logic rather than a real LLM.
- Heading recognition depends on the extracted PDF text and parser rules.
- JSON generation storage is suitable for this prototype but is not designed for concurrent, high-volume production writes.
- Further API, validation, and integration tests are recommended.