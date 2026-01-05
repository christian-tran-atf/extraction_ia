from abc import ABC
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, Json


class SourceEntry(BaseModel):
    id: str
    id_source: Optional[str]
    type_de_document: Optional[str]
    lien_gcs: Optional[str]
    statut_extraction: Optional[str]
    tentatives: Optional[int]
    date_creation: Optional[datetime]
    date_derniere_modification: Optional[datetime]
    tech_interface_id: Optional[str]
    tech_timestamp: Optional[datetime]


class ExtractionOutput(BaseModel, ABC):
    pass


class FRIReportInfo(BaseModel):
    laboratory: str = Field(..., description="Name of the laboratory.")


class FRIExtractionOutput(ExtractionOutput):
    report_info: FRIReportInfo = Field(
        ..., description="Information about the FRI report."
    )


class ValidationOutput(BaseModel, ABC):
    pass


class FRIValidationOutput(ValidationOutput):
    pass


class ProcessingOutput(BaseModel):
    extraction_output: dict[str, Any]
    validation_output: Optional[dict[str, Any]] = None


class DestinationEntry(BaseModel):
    id: str
    type_de_document: Optional[str]
    payload_json: Optional[Json[Any]]
    date_creation: Optional[datetime]
    date_derniere_modification: Optional[datetime]
    tech_interface_id: Optional[str]
    tech_timestamp: Optional[datetime]
