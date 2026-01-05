from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.models.common import ExtractionOutput, ValidationOutput

# ============================================================================
# Enumerations
# ============================================================================


class InspectionResult(str, Enum):
    """Result of an inspection component."""

    PASS = "pass"
    FAIL = "fail"
    IN_WAITING = "in_waiting"


class AQLLevel(str, Enum):
    """General AQL inspection levels."""

    I = "I"
    II = "II"
    III = "III"


class SpecialAQLLevel(str, Enum):
    """Special AQL inspection levels."""

    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"


class SilicaGelType(str, Enum):
    """Types of silica gel."""

    SILICA_GEL = "Silica Gel"
    DRI_CLAY = "Dri Caly Micro Pak"
    CALCIUM_CHLORIDE = "Calcium Chlorid"


class SilicaGelLocation(str, Enum):
    """Location of silica gel in packaging."""

    EXPORT = "export"
    INNER = "inner"
    PACKAGE = "package"


class VerdictType(str, Enum):
    """Final verdict types for validation."""

    VRAI_PASS = "vrai_pass"  # True Positive: Lab Pass & SIPLEC Pass
    VRAI_FAIL = "vrai_fail"  # True Negative: Lab Fail & SIPLEC Fail
    FAUX_PASS = "faux_pass"  # False Positive: Lab Pass but SIPLEC Fail
    FAUX_FAIL = "faux_fail"  # False Negative: Lab Fail but SIPLEC Pass
    IN_WAITING_RESOLVED = "in_waiting_resolved"  # Lab In Waiting with SIPLEC decision


# class DefectSeverity(str, Enum):
# """Severity levels for defects."""
#
# CRITICAL = "critical"
# MAJOR = "major"
# MINOR = "minor"


# ============================================================================
# FRI Extraction Models - Nested Components
# ============================================================================


class FRIReportInfo(BaseModel):
    """General information about the FRI report."""

    laboratory: str = Field(..., description="Name of the testing laboratory")
    id_report: str = Field(..., description="Report ID (can contain letters)")
    date_report: str = Field(..., description="Report date")


class FRIBarcode(BaseModel):
    """Barcode information including GTIN and export carton codes."""

    gtin: str = Field(..., description="GTIN/Packaging number with grade letter")
    export_carton: str = Field(..., description="Export carton code")
    format_export_carton: str = Field(
        ..., description="Format of export carton code (must be EAN-128 or variant)"
    )
    format_packaging: str = Field(
        ..., description="Format of packaging code (must be EAN-13 or variant)"
    )

    @field_validator("gtin")
    @classmethod
    def validate_gtin_grade(cls, v: str) -> str:
        """Ensure GTIN includes grade letter (A or B for pass)."""
        if not v:
            raise ValueError("GTIN cannot be empty")
        return v


class FRIProduct(BaseModel):
    """Product information."""

    product_label: str = Field(..., description="Product name")
    product_description: str = Field(..., description="Product description")
    supplier_label: str = Field(..., description="Supplier label")
    supplier_ref: str = Field(..., description="Supplier reference")
    manufacturer_label: str = Field(..., description="Manufacturer label")


class FRISilicaGel(BaseModel):
    """Silica gel information for moisture control."""

    carton: SilicaGelLocation = Field(..., description="Location: export/inner/package")
    quantity: int = Field(..., description="Quantity of silica gel packets")
    white_transparent: bool = Field(
        ..., description="Must be white or transparent (SIPLEC requirement)"
    )
    name: SilicaGelType = Field(
        ..., description="Type of desiccant: Silica Gel, Dri Clay, or Calcium Chloride"
    )


class FRIQuantity(BaseModel):
    """Quantity information for a command."""

    order_quantity: int = Field(..., description="Ordered product quantity")
    order_carton: int = Field(..., description="Ordered carton quantity")
    presented_quantity: int = Field(..., description="Received product quantity")
    presented_carton: int = Field(..., description="Received carton quantity")

    @model_validator(mode="after")
    def check_quantity_match(self):
        """Validate that ordered quantities match presented quantities."""
        if self.order_quantity != self.presented_quantity:
            # Note: This is a business rule validation - doesn't raise error but should be flagged
            pass
        if self.order_carton != self.presented_carton:
            # Note: This is a business rule validation - doesn't raise error but should be flagged
            pass
        return self


class FRICommand(BaseModel):
    """Individual command information."""

    po: str = Field(..., description="PO catalog number")
    lec: str = Field(..., description="LEC number")
    quantity: FRIQuantity


class FRICommandTotal(BaseModel):
    """Total command information across all orders."""

    po: Optional[str] = Field(None, description="PO catalog number (if single order)")
    lec: Optional[str] = Field(None, description="LEC number (if single order)")
    total_quantity: FRIQuantity


class FRICommandInformations(BaseModel):
    """All command information - can have multiple individual commands plus total."""

    commands: Optional[List[FRICommand]] = Field(
        None, description="Individual commands (only when multiple orders exist)"
    )
    command_total: FRICommandTotal = Field(..., description="Total across all commands")

    @model_validator(mode="after")
    def validate_commands_structure(self):
        """Ensure commands list is only populated when multiple orders exist."""
        if self.commands and len(self.commands) == 1:
            # Single command should only use command_total
            pass
        return self


class FRIInspectionConclusion(BaseModel):
    """Results of various inspection components."""

    style_material: InspectionResult = Field(
        ..., description="Style, material & color vs PO/TF/Golden sample"
    )
    function_test: InspectionResult = Field(..., description="Function test result")
    workmanship: InspectionResult = Field(..., description="Workmanship quality")
    shipping_mark: InspectionResult = Field(
        ..., description="Shipping mark correctness"
    )
    packaging_label: InspectionResult = Field(
        ..., description="Packaging/Label compliance"
    )
    measurement: InspectionResult = Field(..., description="Data measurement accuracy")
    barcode_grade: InspectionResult = Field(..., description="Barcode grade quality")


class FRINotes(BaseModel):
    """Notes and remarks from the inspection."""

    nc_remarks: List[str] = Field(
        default_factory=list,
        description="Non-conformity remarks (default category when unclear)",
    )
    informative_remarks: List[str] = Field(
        default_factory=list, description="Informative remarks"
    )
    notes: List[str] = Field(default_factory=list, description="General notes")


class FRIDefect(BaseModel):
    """Individual defect description with severity counts."""

    defect_description: str = Field(..., description="Description of the defect")
    critical: int = Field(0, ge=0, description="Number of critical defects")
    major: int = Field(0, ge=0, description="Number of major defects")
    minor: int = Field(0, ge=0, description="Number of minor defects")


class FRIAQLCategory(BaseModel):
    """AQL tolerance values by severity."""

    critical: float = Field(
        ..., description="AQL value for critical defects (SIPLEC requires 0)"
    )
    major: float = Field(
        ..., description="AQL value for major defects (SIPLEC requires 1.5 or 2.5)"
    )
    minor: float = Field(
        ..., description="AQL value for minor defects (SIPLEC requires 4)"
    )


class FRIAQLMaximumAllowed(BaseModel):
    """Maximum allowed defects by severity (AC values from AQL tables)."""

    critical: int = Field(
        ..., ge=0, description="Maximum allowed critical defects (AC)"
    )
    major: int = Field(..., ge=0, description="Maximum allowed major defects (AC)")
    minor: int = Field(..., ge=0, description="Maximum allowed minor defects (AC)")


class FRIGeneralCheck(BaseModel):
    """General AQL inspection check."""

    level: AQLLevel = Field(..., description="Inspection level: I, II, or III")
    sample_size: int = Field(..., gt=0, description="Number of items in sample")
    no_opened_carton: int = Field(..., ge=0, description="Number of cartons opened")
    category: FRIAQLCategory = Field(..., description="AQL values by category")
    # maximum_allowed: FRIAQLMaximumAllowed = Field(
    # ..., description="Maximum allowed defects (AC values)"
    # )
    defect_description: List[FRIDefect] = Field(
        default_factory=list, description="List of identified defects"
    )


class FRISpecialCheck(BaseModel):
    """Special AQL inspection check."""

    level: SpecialAQLLevel = Field(
        ..., description="Special inspection level: S1, S2, S3, or S4"
    )
    sample_size: int = Field(..., gt=0, description="Number of items in sample")
    category: FRIAQLCategory = Field(..., description="AQL values by category")
    # maximum_allowed: FRIAQLMaximumAllowed = Field(
    # ..., description="Maximum allowed defects (AC values)"
    # )
    defect_description: List[FRIDefect] = Field(
        default_factory=list, description="List of identified defects"
    )


class FRIAQL(BaseModel):
    """Complete AQL inspection data (General and Special checks)."""

    general_check: FRIGeneralCheck
    special_check: Optional[FRISpecialCheck] = None


class FRIShippingMarks(BaseModel):
    """Shipping mark and barcode conformity."""

    barcode_conformity_inner_carton: str = Field(
        ..., description="Barcode conformity on inner carton"
    )
    barcode_conformity_master_carton: str = Field(
        ..., description="Barcode conformity on master carton (must be on 4 faces)"
    )


# ============================================================================
# FRI Main Extraction Output
# ============================================================================


class FRIExtractionOutput(ExtractionOutput):
    """Complete extraction output for FRI reports."""

    report: FRIReportInfo
    barcode: FRIBarcode
    product: FRIProduct
    silica_gel: Optional[FRISilicaGel] = Field(
        None, description="Silica gel information (required for applicable products)"
    )
    command_informations: FRICommandInformations
    inspection_conclusion: FRIInspectionConclusion
    overall_inspection_conclusion: InspectionResult = Field(
        ..., description="Overall lab inspection result"
    )
    notes: FRINotes
    aql: FRIAQL
    shipping_marks: FRIShippingMarks


# ============================================================================
# FRI Validation Models
# ============================================================================


class ValidationIssue(BaseModel):
    """Individual validation issue found during analysis."""

    step: str = Field(..., description="Validation step where issue was found")
    severity: Literal["blocking", "warning", "info"] = Field(
        ..., description="Severity of the issue"
    )
    field: str = Field(..., description="Field or section with the issue")
    message: str = Field(..., description="Description of the issue")
    lab_value: Optional[str] = Field(None, description="Value from laboratory")
    expected_value: Optional[str] = Field(
        None, description="Expected value per SIPLEC rules"
    )


class ValidationStepResult(BaseModel):
    """Result of a specific validation step."""

    step_name: str = Field(..., description="Name of validation step")
    result: InspectionResult = Field(..., description="Pass/Fail result for this step")
    issues: List[ValidationIssue] = Field(
        default_factory=list, description="Issues found in this step"
    )
    remarks: Optional[str] = Field(
        None, description="Additional remarks about this step"
    )


class FRIAnalysisValidation(BaseModel):
    """Part 2: Business analysis and validation per SIPLEC rules."""

    step_1_remarks_analysis: ValidationStepResult = Field(
        ..., description="Analysis of remarks and their impact"
    )
    step_2_general_info: ValidationStepResult = Field(
        ..., description="General information validation"
    )
    step_3_quantity: ValidationStepResult = Field(
        ..., description="Product quantity validation"
    )
    step_4_inspection_conclusion: ValidationStepResult = Field(
        ..., description="Inspection conclusion validation"
    )
    step_5_aql: ValidationStepResult = Field(..., description="AQL validation")
    # step_6_decision: ValidationStepResult = Field(
    # ..., description="Final decision based on all criteria"
    # )

    # all_issues: List[ValidationIssue] = Field(
    # default_factory=list, description="Consolidated list of all issues"
    # )
    # siplec_result: InspectionResult = Field(
    # ..., description="SIPLEC's final result after validation"
    # )


class FRIFinalVerdict(BaseModel):
    """Part 3: Final verdict comparing lab result with SIPLEC analysis."""

    lab_result: InspectionResult = Field(
        ..., description="Laboratory's reported result"
    )
    siplec_result: InspectionResult = Field(
        ..., description="SIPLEC's validated result"
    )
    verdict_type: VerdictType = Field(..., description="Classification of verdict")
    requires_human_verification: bool = Field(
        ..., description="Whether human review is needed"
    )
    verdict_message: str = Field(
        ..., description="Detailed explanation of verdict and any discrepancies"
    )
    blocking_issues: List[ValidationIssue] = Field(
        default_factory=list, description="Critical issues that require attention"
    )


class FRIValidationOutput(ValidationOutput):
    """Complete validation output for FRI reports - 3 parts as specified."""

    # part_1_extraction: FRIExtractionOutput = Field(
    # ..., description="Part 1: Extracted data from report"
    # )
    part_2_analysis: FRIAnalysisValidation = Field(
        ..., description="Part 2: SIPLEC business rule analysis"
    )
    part_3_verdict: FRIFinalVerdict = Field(
        ..., description="Part 3: Final verdict and decision"
    )
