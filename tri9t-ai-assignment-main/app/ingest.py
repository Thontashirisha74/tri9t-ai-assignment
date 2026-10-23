
import hashlib
import json
import sys
import uuid
from pathlib import Path

from database import (
    Base,
    Document,
    DocumentVersion,
    SectionNode,
    SessionLocal,
    engine,
)
from parser import parse_pdf

Base.metadata.create_all(bind=engine)


def stable_logical_id(section_number, heading, parent_logical_id):
    """Create a repeatable identity for a logical section."""
    identity = (
        f"{parent_logical_id or 'root'}|"
        f"{section_number or ''}|{heading.strip().casefold()}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def ingest_tree(session, document, version_number, pdf_path):
    existing = (
        session.query(DocumentVersion)
        .filter_by(
            document_id=document.id,
            version_number=version_number,
        )
        .first()
    )
    if existing:
        raise ValueError(
            f"Version {version_number} already exists. "
            "Existing versions are preserved and cannot be overwritten."
        )

    tree = parse_pdf(pdf_path)
    version = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=document.id,
        version_number=version_number,
        source_filename=Path(pdf_path).name,
    )
    session.add(version)
    session.flush()

    def save_node(node, parent_db_id=None, parent_logical_id=None):
        logical_id = stable_logical_id(
            node.get("section_number"),
            node["heading"],
            parent_logical_id,
        )
        db_node = SectionNode(
            id=str(uuid.uuid4()),
            version_id=version.id,
            logical_id=logical_id,
            section_number=node.get("section_number"),
            heading=node["heading"],
            level=node["level"],
            body_text=node.get("body_text", ""),
            content_hash=node["content_hash"],
            parent_id=parent_db_id,
            page_start=node.get("page_start"),
            page_end=node.get("page_end"),
        )
        session.add(db_node)
        session.flush()

        for child in node.get("children", []):
            save_node(child, db_node.id, logical_id)

    save_node(tree)
    session.commit()
    return version


def compare_versions(session, document_id, old_number, new_number):
    old_version = session.query(DocumentVersion).filter_by(
        document_id=document_id,
        version_number=old_number,
    ).one()

    new_version = session.query(DocumentVersion).filter_by(
        document_id=document_id,
        version_number=new_number,
    ).one()

    old_nodes = session.query(SectionNode).filter_by(
        version_id=old_version.id
    ).all()

    new_nodes = session.query(SectionNode).filter_by(
        version_id=new_version.id
    ).all()

    # Match nodes by stable logical ID.
    old_by_logical = {node.logical_id: node for node in old_nodes}
    new_by_logical = {node.logical_id: node for node in new_nodes}

    changes = []

    for logical_id, new_node in new_by_logical.items():
        old_node = old_by_logical.get(logical_id)

        if old_node is None:
            status = "added"
        elif old_node.content_hash != new_node.content_hash:
            status = "changed"
        else:
            status = "unchanged"

        changes.append({
            "status": status,
            "section_number": new_node.section_number,
            "heading": new_node.heading,
            "old_hash": old_node.content_hash if old_node else None,
            "new_hash": new_node.content_hash,
        })

    # Sections present in V1 but absent in V2.
    for logical_id, old_node in old_by_logical.items():
        if logical_id not in new_by_logical:
            changes.append({
                "status": "removed",
                "section_number": old_node.section_number,
                "heading": old_node.heading,
                "old_hash": old_node.content_hash,
                "new_hash": None,
            })

    return changes


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python app\\ingest.py "
            "PDF_PATH VERSION_NUMBER"
        )
        raise SystemExit(1)

    pdf_path = Path(sys.argv[1])
    version_number = int(sys.argv[2])

    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    session = SessionLocal()
    try:
        document = session.query(Document).filter_by(
            name="CardioTrack CT-200 Manual"
        ).first()

        if document is None:
            document = Document(
                id=str(uuid.uuid4()),
                name="CardioTrack CT-200 Manual",
            )
            session.add(document)
            session.commit()

        version = ingest_tree(
            session, document, version_number, pdf_path
        )
        print(
            f"Ingested version {version.version_number}: "
            f"{version.source_filename}"
        )
        print(f"Document ID: {document.id}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
