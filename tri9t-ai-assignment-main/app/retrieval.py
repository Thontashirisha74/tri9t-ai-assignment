
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from database import SessionLocal, SectionNode, DocumentVersion

router = APIRouter(tags=["Generated Test Retrieval"])

BASE_DIR = Path(__file__).resolve().parent.parent
GENERATIONS_FILE = BASE_DIR / "generated" / "generations.json"


def load_generations():
    if not GENERATIONS_FILE.exists():
        return []
    return json.loads(GENERATIONS_FILE.read_text(encoding="utf-8"))


def refresh_staleness(generation):
    session = SessionLocal()
    try:
        stale_sources = []

        for source in generation.get("source_sections", []):
            source_node = session.query(SectionNode).filter_by(
                id=source["node_id"],
                version_id=source["version_id"],
            ).first()

            if source_node is None:
                stale_sources.append({
                    "node_id": source["node_id"],
                    "reason": "Original source section is missing",
                })
                continue

            # Find the newest version of this document.
            source_version = session.query(DocumentVersion).filter_by(
                id=source["version_id"]
            ).first()

            if source_version is None:
                stale_sources.append({
                    "node_id": source["node_id"],
                    "reason": "Original source version is missing",
                })
                continue

            latest_version = session.query(DocumentVersion).filter_by(
                document_id=source_version.document_id,
            ).order_by(DocumentVersion.version_number.desc()).first()

            if latest_version is None:
                continue

            latest_node = session.query(SectionNode).filter_by(
                version_id=latest_version.id,
                logical_id=source_node.logical_id,
            ).first()

            if latest_node is None:
                stale_sources.append({
                    "node_id": source["node_id"],
                    "reason": "Source section was removed in a newer version",
                })
            elif latest_node.content_hash != source["content_hash"]:
                stale_sources.append({
                    "node_id": source["node_id"],
                    "reason": "Source section changed in a newer version",
                    "latest_version": latest_version.version_number,
                })

        result = dict(generation)
        result["stale"] = bool(stale_sources)
        result["stale_sources"] = stale_sources
        return result

    finally:
        session.close()


@router.get("/generations")
def get_generations(
    selection_id: str | None = None,
    node_id: str | None = None,
):
    if not selection_id and not node_id:
        raise HTTPException(
            status_code=422,
            detail="Provide selection_id or node_id",
        )

    generations = load_generations()
    results = []

    for generation in generations:
        matches_selection = (
            selection_id is not None
            and generation.get("selection_id") == selection_id
        )
        matches_node = (
            node_id is not None
            and any(
                source.get("node_id") == node_id
                for source in generation.get("source_sections", [])
            )
        )

        if matches_selection or matches_node:
            results.append(refresh_staleness(generation))

    return results


@router.get("/generations/{generation_id}")
def get_generation(generation_id: str):
    for generation in load_generations():
        if generation.get("generation_id") == generation_id:
            return refresh_staleness(generation)

    raise HTTPException(status_code=404, detail="Generation not found")
