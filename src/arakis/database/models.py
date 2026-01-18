"""Database models for Arakis systematic review platform."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Workflow(Base):
    """Systematic review workflow."""

    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    research_question = Column(Text, nullable=False)
    inclusion_criteria = Column(Text)
    exclusion_criteria = Column(Text)
    databases = Column(JSON)  # ["pubmed", "openalex", ...]
    status = Column(
        String(20), default="pending"
    )  # "pending", "running", "needs_review", "completed", "failed"
    current_stage = Column(
        String(50), nullable=True
    )  # "searching", "screening", "analyzing", "writing", "finalizing"

    # Statistics
    papers_found = Column(Integer, default=0)
    papers_screened = Column(Integer, default=0)
    papers_included = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # User and trial tracking
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(64), nullable=True, index=True)  # For anonymous trial tracking

    # Relationships
    user = relationship("User", back_populates="workflows")
    papers = relationship("Paper", back_populates="workflow", cascade="all, delete-orphan")
    screening_decisions = relationship(
        "ScreeningDecision", back_populates="workflow", cascade="all, delete-orphan"
    )
    extractions = relationship(
        "Extraction", back_populates="workflow", cascade="all, delete-orphan"
    )
    manuscript = relationship(
        "Manuscript", back_populates="workflow", uselist=False, cascade="all, delete-orphan"
    )


class Paper(Base):
    """Academic paper from literature search."""

    __tablename__ = "papers"

    id = Column(String(100), primary_key=True)  # e.g., "pubmed_12345"
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)

    # Identifiers
    doi = Column(String(255), nullable=True, index=True)
    pmid = Column(String(20), nullable=True, index=True)
    pmcid = Column(String(20), nullable=True, index=True)
    arxiv_id = Column(String(50), nullable=True)
    s2_id = Column(String(50), nullable=True)
    openalex_id = Column(String(100), nullable=True)

    # Metadata
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    journal = Column(String(500))
    year = Column(Integer)
    authors = Column(JSON)  # List of {name, affiliation, orcid}
    keywords = Column(JSON)  # List of strings
    mesh_terms = Column(JSON)  # List of strings

    # Full text
    full_text = Column(Text, nullable=True)
    full_text_extracted_at = Column(DateTime, nullable=True)
    text_extraction_method = Column(String(20))  # "pymupdf", "pdfplumber", "ocr"
    text_quality_score = Column(Float)

    # Access
    pdf_url = Column(String(1000))
    pdf_file_path = Column(String(1000))  # S3/MinIO path
    open_access = Column(Boolean, default=False)

    # Source
    source = Column(String(50))  # "pubmed", "openalex", etc.
    source_url = Column(String(1000))
    retrieved_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="papers")
    screening_decision = relationship("ScreeningDecision", back_populates="paper", uselist=False)
    extraction = relationship("Extraction", back_populates="paper", uselist=False)


class ScreeningDecision(Base):
    """AI-powered screening decision for a paper."""

    __tablename__ = "screening_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    paper_id = Column(String(100), ForeignKey("papers.id"), nullable=False)

    # Decision
    status = Column(String(20), nullable=False)  # "INCLUDE", "EXCLUDE", "MAYBE"
    reason = Column(Text)
    confidence = Column(Float)  # 0.0-1.0

    # Matched criteria
    matched_inclusion = Column(JSON)  # List of matched inclusion criteria
    matched_exclusion = Column(JSON)  # List of matched exclusion criteria

    # Dual review support
    is_conflict = Column(Boolean, default=False)
    second_opinion = Column(JSON, nullable=True)  # Second reviewer's decision

    # Human review
    human_reviewed = Column(Boolean, default=False)
    ai_decision = Column(String(20), nullable=True)  # Original AI decision
    human_decision = Column(String(20), nullable=True)  # Human override
    overridden = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="screening_decisions")
    paper = relationship("Paper", back_populates="screening_decision")


class Extraction(Base):
    """Structured data extraction from a paper."""

    __tablename__ = "extractions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    paper_id = Column(String(100), ForeignKey("papers.id"), nullable=False)

    # Schema
    schema_name = Column(String(50), nullable=False)  # "rct", "cohort", "case_control"
    extraction_method = Column(String(50))  # "TRIPLE_REVIEW", "SINGLE_PASS"

    # Extracted data
    data = Column(JSON, nullable=False)  # {field_name: value}
    confidence = Column(JSON)  # {field_name: confidence_score}

    # Quality metrics
    extraction_quality = Column(Float)  # 0.0-1.0
    needs_human_review = Column(Boolean, default=False)
    conflicts = Column(JSON)  # List of fields with conflicts

    # Metadata
    reviewer_decisions = Column(JSON)  # List of individual reviewer decisions (for triple-review)
    low_confidence_fields = Column(JSON)  # List of fields below confidence threshold

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="extractions")
    paper = relationship("Paper", back_populates="extraction")


class Manuscript(Base):
    """Generated manuscript for systematic review."""

    __tablename__ = "manuscripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False, unique=True)

    # Content (Markdown)
    title = Column(Text)
    abstract = Column(Text)
    introduction = Column(Text)
    methods = Column(Text)
    results = Column(Text)
    discussion = Column(Text)
    conclusions = Column(Text)

    # References
    references = Column(JSON)  # List of {id, citation, doi, etc.}

    # Figures and tables
    figures = Column(JSON)  # {id: {title, caption, path, type}}
    tables = Column(JSON)  # {id: {title, headers, rows, footnotes}}

    # Metadata (renamed to 'meta' to avoid conflict with SQLAlchemy's reserved 'metadata')
    meta = Column(JSON)  # {authors, affiliations, keywords, funding, etc.}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    workflow = relationship("Workflow", back_populates="manuscript")


class User(Base):
    """User account with OAuth support."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth-only users
    full_name = Column(String(255))
    phone_number = Column(String(20), nullable=True)
    affiliation = Column(String(500))

    # OAuth fields
    apple_id = Column(String(255), unique=True, nullable=True, index=True)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    avatar_url = Column(String(1000), nullable=True)
    email_verified = Column(Boolean, default=False)
    auth_provider = Column(String(20), default="email")  # "email", "apple", "google"

    # Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # API usage tracking (optional)
    total_workflows = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # Relationships
    workflows = relationship("Workflow", back_populates="user")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Refresh token for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), nullable=False, index=True)
    device_info = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
