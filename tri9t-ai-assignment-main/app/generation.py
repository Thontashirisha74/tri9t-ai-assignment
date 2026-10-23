
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from database import (
    SessionLocal,
    Selection,
    SelectionItem,
    SectionNode,
    DocumentVersion,
)

router = APIRouter(tags=["Test Generation"])

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)
GENERATIONS_FILE = GENERATED_DIR / "generations.json"


class TestCase(BaseModel):
    title: str = Field(min_length=3)
    preconditions: list[str] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    expected_result: str = Field(min_length=5)


class GeneratedTestCases(BaseModel):
    test_cases: list[TestCase] = Field(min_length=3, max_length=5)


def load_generations():
    if not GENERATIONS_FILE.exists():
        return []
    return json.loads(GENERATIONS_FILE.read_text(encoding="utf-8"))


def save_generations(generations):
    temp_file = GENERATIONS_FILE.with_suffix(".tmp")
    temp_file.write_text(
        json.dumps(generations, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temp_file.replace(GENERATIONS_FILE)



import re


def mock_generate(section):
    """Development-only test cases based on the selected section text."""
    text = section["body_text"]
    normalized_text = text.casefold()
    heading = section["heading"]

    if "battery" in heading.casefold() or "battery" in normalized_text:
        # Extract values from the selected version instead of hardcoding V2.
        cycles_match = re.search(
            r"approximately\s+(\d+)\s+measurement cycles",
            text,
            re.IGNORECASE,
        )
        threshold_match = re.search(
            r"below\s+(\d+(?:\.\d+)?)%",
            text,
            re.IGNORECASE,
        )

        cycles = cycles_match.group(1) if cycles_match else None
        threshold = threshold_match.group(1) if threshold_match else None

        tests = []

        if cycles is not None:
            tests.append(
                TestCase(
                    title="Verify battery measurement-cycle estimate",
                    preconditions=[
                        "Use the CT-200 with four AA alkaline batteries."
                    ],
                    steps=[
                        "Review the selected section's battery-life specification.",
                        "Compare the stated measurement-cycle estimate.",
                    ],
                    expected_result=(
                        f"The selected section specifies approximately "
                        f"{cycles} measurement cycles."
                    ),
                )
            )

        if threshold is not None:
            tests.append(
                TestCase(
                    title="Verify low-battery threshold",
                    preconditions=[
                        "The selected manual section is available."
                    ],
                    steps=[
                        "Review the low-battery threshold in the selected section.",
                        "Compare the stated threshold with the specification.",
                    ],
                    expected_result=(
                        f"The low-battery icon is specified to appear "
                        f"below {threshold}% remaining capacity."
                    ),
                )
            )

        tests.append(
            TestCase(
                title="Verify battery information traceability",
                preconditions=[
                    "A version-pinned selection exists."
                ],
                steps=[
                    "Retrieve the selected section and its content hash.",
                    "Compare the generated test's source metadata with the selection.",
                ],
                expected_result=(
                    f"The test is traceable to section {section.get('section_number', heading)} "
                    f"from the selected manual version."
                ),
            )
        )

        # The API requires between 3 and 5 test cases.
        while len(tests) < 3:
            tests.append(
                TestCase(
                    title="Verify battery specification traceability",
                    preconditions=["The selected section is stored."],
                    steps=[
                        "Read the selected battery specification.",
                        "Verify the recorded source version and content hash.",
                    ],
                    expected_result=(
                        "The test references the selected section and version."
                    ),
                )
            )

        return GeneratedTestCases(test_cases=tests[:5])

    tests = [
        TestCase(
            title=f"Review selected section: {heading}",
            preconditions=["The selected manual section is available."],
            steps=[
                f"Retrieve the text for {heading}.",
                "Compare the expected behavior with the section text.",
            ],
            expected_result=(
                f"The behavior recorded for {heading} matches the selected section text."
            ),
        ),
        TestCase(
            title=f"Verify source version for {heading}",
            preconditions=["A version-pinned selection exists."],
            steps=[
                "Read the selected section and its version number.",
                "Confirm the test uses the pinned version.",
            ],
            expected_result=(
                "The test uses the section from the selected manual version."
            ),
        ),
        TestCase(
            title=f"Verify traceability for {heading}",
            preconditions=["The selected section has a content hash."],
            steps=[
                "Retrieve the selected section ID and content hash.",
                "Compare them with the generation's recorded source metadata.",
            ],
            expected_result=(
                "The test output can be traced to the selected source section."
            ),
        ),
    ]

    return GeneratedTestCases(test_cases=tests)



@router.post("/selections/{selection_id}/generate", status_code=201)
def generate_tests(selection_id: str):
    session = SessionLocal()
    try:
        selection = session.query(Selection).filter_by(
            id=selection_id
        ).first()

        if selection is None:
            raise HTTPException(status_code=404, detail="Selection not found")

        items = session.query(SelectionItem).filter_by(
            selection_id=selection_id
        ).all()

        if not items:
            raise HTTPException(
                status_code=422,
                detail="Selection contains no sections",
            )

        source_sections = []
        all_test_cases = []

        for item in items:
            node = session.query(SectionNode).filter_by(
                id=item.node_id,
                version_id=item.version_id,
            ).first()

            version = session.query(DocumentVersion).filter_by(
                id=item.version_id
            ).first()

            if node is None or version is None:
                raise HTTPException(
                    status_code=422,
                    detail="A selected source section is unavailable",
                )

            source = {
                "node_id": node.id,
                "version_id": version.id,
                "version_number": version.version_number,
                "section_number": node.section_number,
                "heading": node.heading,
                "content_hash": node.content_hash,
                "body_text": node.body_text,
            }
            source_sections.append(source)

            validated = mock_generate(source)
            for case in validated.test_cases:
                all_test_cases.append({
                    **case.model_dump(),
                    "source_node_id": node.id,
                    "source_version": version.version_number,
                    "source_hash": node.content_hash,
                })

        generation = {
            "generation_id": str(uuid.uuid4()),
            "selection_id": selection_id,
            "selection_name": selection.name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "provider": "mock",
            "notice": (
                "Development mock output; not generated by a real LLM."
            ),
            "source_sections": source_sections,
            "test_cases": all_test_cases,
            "stale": False,
        }

        generations = load_generations()
        generations.append(generation)
        save_generations(generations)

        return generation

    except (ValidationError, ValueError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"Generated output failed validation: {exc}",
        ) from exc
    finally:
        session.close()
