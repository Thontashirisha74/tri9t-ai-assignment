
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy.orm import Session
from generation import router as generation_router
from selections import router as selections_router
from retrieval import router as retrieval_router
from database import (
    Base,
    Document,
    DocumentVersion,
    SectionNode,
    SessionLocal,
    engine,
)
from ingest import compare_versions

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CardioTrack Manual Intelligence API",
    description="Versioned manual ingestion, browsing, search, and change detection.",
    version="1.0.0",
)
app.include_router(selections_router)
app.include_router(generation_router)
app.include_router(retrieval_router)

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/documents")
def list_documents():
    session = SessionLocal()
    try:
        documents = session.query(Document).all()
        result = []

        for document in documents:
            versions = session.query(DocumentVersion).filter_by(
                document_id=document.id
            ).order_by(DocumentVersion.version_number).all()

            result.append({
                "id": document.id,
                "name": document.name,
                "versions": [
                    {
                        "version_number": version.version_number,
                        "source_filename": version.source_filename,
                    }
                    for version in versions
                ],
            })

        return result
    finally:
        session.close()


@app.get("/documents/{document_id}/sections")
def list_sections(
    document_id: str,
    version: int = Query(1, ge=1),
):
    session = SessionLocal()
    try:
        doc_version = session.query(DocumentVersion).filter_by(
            document_id=document_id,
            version_number=version,
        ).first()

        if doc_version is None:
            raise HTTPException(status_code=404, detail="Version not found")

        roots = session.query(SectionNode).filter_by(
            version_id=doc_version.id,
            parent_id=None,
        ).all()

        return [
            {
                "id": node.id,
                "section_number": node.section_number,
                "heading": node.heading,
                "level": node.level,
                "content_hash": node.content_hash,
                "page_start": node.page_start,
                "page_end": node.page_end,
                "child_count": len([
                    child for child in session.query(SectionNode).filter_by(
                        parent_id=node.id
                    ).all()
                ]),
            }
            for node in roots
        ]
    finally:
        session.close()


@app.get("/nodes/{node_id}")
def get_node(node_id: str):
    session = SessionLocal()
    try:
        node = session.query(SectionNode).filter_by(id=node_id).first()

        if node is None:
            raise HTTPException(status_code=404, detail="Node not found")

        children = session.query(SectionNode).filter_by(
            parent_id=node.id
        ).all()

        return {
            "id": node.id,
            "version_id": node.version_id,
            "logical_id": node.logical_id,
            "section_number": node.section_number,
            "heading": node.heading,
            "level": node.level,
            "body_text": node.body_text,
            "content_hash": node.content_hash,
            "page_start": node.page_start,
            "page_end": node.page_end,
            "children": [
                {
                    "id": child.id,
                    "section_number": child.section_number,
                    "heading": child.heading,
                    "content_hash": child.content_hash,
                }
                for child in children
            ],
        }
    finally:
        session.close()


@app.get("/search")
def search_nodes(
    q: str = Query(..., min_length=1),
    version: int = Query(1, ge=1),
):
    session = SessionLocal()
    try:
        query = session.query(SectionNode).join(
            DocumentVersion,
            SectionNode.version_id == DocumentVersion.id,
        ).filter(
            DocumentVersion.version_number == version,
            (
                SectionNode.heading.ilike(f"%{q}%")
                | SectionNode.body_text.ilike(f"%{q}%")
            ),
        )

        return [
            {
                "id": node.id,
                "section_number": node.section_number,
                "heading": node.heading,
                "body_text": node.body_text,
                "content_hash": node.content_hash,
            }
            for node in query.all()
        ]
    finally:
        session.close()


@app.get("/documents/{document_id}/changes")
def get_changes(
    document_id: str,
    from_version: int = Query(1, ge=1),
    to_version: int = Query(2, ge=1),
):
    session = SessionLocal()
    try:
        try:
            changes = compare_versions(
                session, document_id, from_version, to_version
            )
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail="Could not compare the requested versions",
            ) from exc

        counts = {
            "added": sum(c["status"] == "added" for c in changes),
            "changed": sum(c["status"] == "changed" for c in changes),
            "removed": sum(c["status"] == "removed" for c in changes),
            "unchanged": sum(c["status"] == "unchanged" for c in changes),
        }

        return {"summary": counts, "changes": changes}
    finally:
        session.close()
