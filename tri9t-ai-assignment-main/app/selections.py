
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import (
    SessionLocal,
    Selection,
    SelectionItem,
    SectionNode,
    DocumentVersion,
)

router = APIRouter(tags=["Selections"])


class SelectedSection(BaseModel):
    node_id: str
    version_number: int = Field(ge=1)


class SelectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    items: list[SelectedSection] = Field(min_length=1)


@router.post("/selections", status_code=201)
def create_selection(request: SelectionCreate):
    session: Session = SessionLocal()

    try:
        selection_id = str(uuid4())

        selection = Selection(
            id=selection_id,
            name=request.name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(selection)
        session.flush()

        # Reject duplicate node/version pairs in one selection.
        pairs = [
            (item.node_id, item.version_number)
            for item in request.items
        ]
        if len(pairs) != len(set(pairs)):
            raise HTTPException(
                status_code=422,
                detail="Duplicate node/version pairs are not allowed",
            )

        saved_items = []

        for item in request.items:
            node = session.query(SectionNode).filter_by(
                id=item.node_id
            ).first()

            if node is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Node not found: {item.node_id}",
                )

            version = session.query(DocumentVersion).filter_by(
                id=node.version_id,
                version_number=item.version_number,
            ).first()

            if version is None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Node {item.node_id} does not belong to "
                        f"version {item.version_number}"
                    ),
                )

            selection_item = SelectionItem(
                id=str(uuid4()),
                selection_id=selection_id,
                node_id=node.id,
                version_id=version.id,
            )
            session.add(selection_item)

            saved_items.append({
                "node_id": node.id,
                "section_number": node.section_number,
                "heading": node.heading,
                "version_number": version.version_number,
                "version_id": version.id,
                "content_hash": node.content_hash,
            })

        session.commit()

        return {
            "selection_id": selection_id,
            "name": selection.name,
            "items": saved_items,
        }

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
