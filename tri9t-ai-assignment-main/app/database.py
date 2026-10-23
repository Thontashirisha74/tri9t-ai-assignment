
from pathlib import Path

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Store the database in the project root
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'cardiotrack.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String, primary_key=True)
    document_id = Column(
        String,
        ForeignKey("documents.id"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    source_filename = Column(String, nullable=False)

    document = relationship("Document", back_populates="versions")
    nodes = relationship(
        "SectionNode",
        back_populates="version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_version",
        ),
    )


class SectionNode(Base):
    __tablename__ = "section_nodes"

    id = Column(String, primary_key=True)
    version_id = Column(
        String,
        ForeignKey("document_versions.id"),
        nullable=False,
    )

    # Stable across versions when the logical section matches
    logical_id = Column(String, nullable=False)

    section_number = Column(String, nullable=True)
    heading = Column(String, nullable=False)
    level = Column(Integer, nullable=False)
    body_text = Column(Text, default="", nullable=False)
    content_hash = Column(String, nullable=False)

    parent_id = Column(
        String,
        ForeignKey("section_nodes.id"),
        nullable=True,
    )

    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)

    version = relationship("DocumentVersion", back_populates="nodes")


class Selection(Base):
    __tablename__ = "selections"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class SelectionItem(Base):
    __tablename__ = "selection_items"

    id = Column(String, primary_key=True)
    selection_id = Column(
        String,
        ForeignKey("selections.id"),
        nullable=False,
    )
    node_id = Column(
        String,
        ForeignKey("section_nodes.id"),
        nullable=False,
    )
    version_id = Column(
        String,
        ForeignKey("document_versions.id"),
        nullable=False,
    )
