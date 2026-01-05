from abc import ABC
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Json


class SourceEntry(BaseModel):
    """Entry from source system."""

    id: str
    id_source: Optional[str] = None
    type_de_document: Optional[str] = None
    lien_gcs: Optional[str] = None
    statut_extraction: Optional[str] = None
    tentatives: Optional[int] = None
    date_creation: Optional[datetime] = None
    date_derniere_modification: Optional[datetime] = None
    tech_interface_id: Optional[str] = None
    tech_timestamp: Optional[datetime] = None


class DestinationEntry(BaseModel):
    """Entry for destination system."""

    id: str
    type_de_document: Optional[str] = None
    payload_json: Optional[Json[Any]] = None
    date_creation: Optional[datetime] = None
    date_derniere_modification: Optional[datetime] = None
    tech_interface_id: Optional[str] = None
    tech_timestamp: Optional[datetime] = None


class ExtractionOutput(BaseModel, ABC):
    """Abstract base class for extraction outputs."""

    pass


class ValidationOutput(BaseModel, ABC):
    """Abstract base class for validation outputs."""

    pass


class ProcessingOutput(BaseModel):
    """Combined processing output for the pipeline."""

    extraction_output: dict[str, Any]
    validation_output: Optional[dict[str, Any]] = None
