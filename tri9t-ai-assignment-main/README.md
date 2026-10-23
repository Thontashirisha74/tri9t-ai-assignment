# CardioTrack CT-200 Manual Analysis API

## Overview

A FastAPI backend for ingesting, versioning, browsing, and comparing CardioTrack CT-200 blood pressure monitor manuals. It supports version-pinned section selections, structured test-case generation, and stale-result detection.

## Features

- PDF text extraction and hierarchical section parsing.
- Multiple manual versions stored using SQLite and SQLAlchemy.
- Stable logical section identifiers and content hashes.
- Section browsing, node retrieval, and text search.
- Version comparison with added, changed, removed, and unchanged sections.
- Version-pinned selections.
- Structured test-case generation with source metadata.
- Retrieval of generated results with staleness checks.

## Technology Stack

Python 3.11, FastAPI, Pydantic, SQLAlchemy, SQLite, pypdf, JSON, and pytest.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Ingest the Manuals

Run from the project root:

```powershell
python app\parser.py data\ct200_manual.pdf generated\ct200_v1_tree.json
python app\parser.py data\ct200_manual_v2.pdf generated\ct200_v2_tree.json
python app\ingest.py data\ct200_manual.pdf 1
python app\ingest.py data\ct200_manual_v2.pdf 2
```

Do not rerun ingestion for an existing version unless the application supports that operation.

## Run the API

```powershell
python -m uvicorn main:app --app-dir app --reload
```

Interactive API documentation: http://127.0.0.1:8000/docs

## Run Tests

```powershell
python -m pytest -v
```

The current automated test suite contains seven passing parser and API tests.

## Generated Test Cases

The current implementation uses a development mock generator, not a real LLM. It produces structured test cases from selected section text and stores generation records in `generated/generations.json`.

## Staleness Detection

Generated records retain their source node IDs, version IDs, version numbers, and content hashes. On retrieval, source sections are checked against the latest available version. Changed or removed sections are flagged as stale.

## Project Structure

- `app/` — parser, ingestion, database models, API routes, selections, generation, and retrieval.
- `data/` — source PDF manuals.
- `generated/` — parsed trees and generated records.
- `tests/` — automated tests.
- `approach.md` — implementation approach.
- `decision_log.md` — design decisions and prompts.
- `requirements.txt` — Python dependencies.

## Limitations

The generator currently uses mock logic rather than a real LLM integration. The project is a prototype and would benefit from additional integration tests and production-grade persistence for generation records.