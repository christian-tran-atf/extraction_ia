"""
Helper utilities for FRI report processing.

This module provides utility functions for working with FRI Pydantic models,
including schema generation, validation helpers, and business rule checkers.
"""

from typing import Any, Dict, List, Optional, Tuple

from models.fri import (
    AQLLevel,
    FRIExtractionOutput,
    FRIValidationOutput,
    InspectionResult,
    SpecialAQLLevel,
    ValidationIssue,
    VerdictType,
)

# ============================================================================
# Schema Generation
# ============================================================================


def get_extraction_schema() -> Dict[str, Any]:
    """
    Get JSON schema for FRI extraction output.

    Use this to provide the schema to LLM for structured output generation.

    Returns:
        Dict containing JSON schema
    """
    return FRIExtractionOutput.model_json_schema()


def get_validation_schema() -> Dict[str, Any]:
    """
    Get JSON schema for FRI validation output.

    Returns:
        Dict containing JSON schema
    """
    return FRIValidationOutput.model_json_schema()


# ============================================================================
# Business Rule Helpers
# ============================================================================


def check_gtin_grade(gtin: str) -> Tuple[bool, str]:
    """
    Check if GTIN grade letter indicates PASS.

    Business Rule: Grade must be A or B for PASS; C, D, or E means FAIL.

    Args:
        gtin: GTIN string with grade letter

    Returns:
        Tuple of (is_pass, grade_letter)
    """
    # Extract last character (grade letter)
    if not gtin:
        return False, ""

    grade = gtin[-1].upper()
    if grade in ["A", "B"]:
        return True, grade
    elif grade in ["C", "D", "E"]:
        return False, grade
    else:
        # No clear grade or unexpected format
        return False, grade


def check_ean_format(format_str: str, expected_type: str) -> bool:
    """
    Check if barcode format matches expected type (EAN-13 or EAN-128).

    Accepts variants like "Code 13" for EAN-13.

    Args:
        format_str: Format string from report
        expected_type: "EAN-13" or "EAN-128"

    Returns:
        True if format matches (including variants)
    """
    format_upper = format_str.upper().replace(" ", "").replace("-", "")
    expected_upper = expected_type.upper().replace(" ", "").replace("-", "")

    if expected_upper in format_upper:
        return True

    # Check for known variants
    if expected_type == "EAN-13":
        variants = ["CODE13", "EAN13", "GTIN13"]
    elif expected_type == "EAN-128":
        variants = ["CODE128", "EAN128", "GS1128"]
    else:
        variants = []

    return any(variant in format_upper for variant in variants)


def check_quantity_match(order: int, presented: int) -> Tuple[bool, Optional[str]]:
    """
    Check if order quantity matches presented quantity.

    Args:
        order: Ordered quantity
        presented: Presented/received quantity

    Returns:
        Tuple of (is_match, issue_message)
    """
    if order == presented:
        return True, None
    else:
        return False, f"Quantity mismatch: ordered {order}, presented {presented}"


def check_silica_gel_conformity(
    white_transparent: bool, name: str
) -> Tuple[bool, Optional[str]]:
    """
    Check silica gel conformity per SIPLEC rules.

    Args:
        white_transparent: Must be True
        name: Type of silica gel

    Returns:
        Tuple of (is_conformant, issue_message)
    """
    if not white_transparent:
        return (
            False,
            f"Silica gel must be white or transparent, but it is not (type: {name})",
        )
    return True, None


def check_shipping_mark_conformity(
    master_carton_value: str, inner_carton_value: str
) -> Tuple[bool, List[str]]:
    """
    Check if shipping marks are conformant.

    Business Rule: Gencode must be present on 4 main faces of master carton.

    Args:
        master_carton_value: Value from report for master carton
        inner_carton_value: Value from report for inner carton

    Returns:
        Tuple of (is_conformant, list_of_issues)
    """
    issues = []

    # Check if mentions 4 faces for master carton
    if "4" not in master_carton_value and "four" not in master_carton_value.lower():
        issues.append("Master carton must have gencode on 4 main faces")

    # Additional checks can be added here

    return len(issues) == 0, issues


# ============================================================================
# AQL Helpers
# ============================================================================


def check_aql_sample_size(
    order_quantity: int, level: AQLLevel, sample_size: int
) -> Tuple[bool, Optional[str]]:
    """
    Check if AQL sample size is sufficient.

    Note: This is a simplified check. In production, you should integrate
    with actual AQL lookup tables (General/Special Inspection Level files).

    Args:
        order_quantity: Total order quantity
        level: AQL level (I, II, or III)
        sample_size: Actual sample size taken

    Returns:
        Tuple of (is_sufficient, issue_message)
    """
    # TODO: Implement lookup from AQL tables
    # This is a placeholder that always returns True
    return True, None


def check_aql_defects(
    critical_count: int,
    major_count: int,
    minor_count: int,
    critical_ac: int,
    major_ac: int,
    minor_ac: int,
) -> Tuple[bool, List[str]]:
    """
    Check if defect counts are within acceptable limits.

    Business Rules:
    - Critical defects must be ≤ AC (typically 0)
    - Major defects must be ≤ AC
    - Minor defects must be ≤ AC

    Args:
        critical_count: Number of critical defects found
        major_count: Number of major defects found
        minor_count: Number of minor defects found
        critical_ac: Accept level for critical (from AQL table)
        major_ac: Accept level for major (from AQL table)
        minor_ac: Accept level for minor (from AQL table)

    Returns:
        Tuple of (is_acceptable, list_of_issues)
    """
    issues = []

    if critical_count > critical_ac:
        issues.append(
            f"Critical defects ({critical_count}) exceed AC limit ({critical_ac})"
        )

    if major_count > major_ac:
        issues.append(f"Major defects ({major_count}) exceed AC limit ({major_ac})")

    if minor_count > minor_ac:
        issues.append(f"Minor defects ({minor_count}) exceed AC limit ({minor_ac})")

    return len(issues) == 0, issues


# ============================================================================
# Verdict Determination
# ============================================================================


def determine_verdict_type(
    lab_result: InspectionResult, siplec_result: InspectionResult
) -> VerdictType:
    """
    Determine the verdict type based on lab and SIPLEC results.

    Args:
        lab_result: Laboratory's inspection result
        siplec_result: SIPLEC's validation result

    Returns:
        VerdictType enum value
    """
    if lab_result == InspectionResult.IN_WAITING:
        return VerdictType.IN_WAITING_RESOLVED

    if lab_result == InspectionResult.PASS and siplec_result == InspectionResult.PASS:
        return VerdictType.VRAI_PASS

    if lab_result == InspectionResult.FAIL and siplec_result == InspectionResult.FAIL:
        return VerdictType.VRAI_FAIL

    if lab_result == InspectionResult.PASS and siplec_result == InspectionResult.FAIL:
        return VerdictType.FAUX_PASS

    if lab_result == InspectionResult.FAIL and siplec_result == InspectionResult.PASS:
        return VerdictType.FAUX_FAIL

    # Default fallback
    return VerdictType.FAUX_PASS


def requires_human_verification(verdict_type: VerdictType) -> bool:
    """
    Check if verdict requires human verification.

    Args:
        verdict_type: Verdict type

    Returns:
        True if human verification required
    """
    return verdict_type in [
        VerdictType.FAUX_PASS,
        VerdictType.FAUX_FAIL,
        VerdictType.IN_WAITING_RESOLVED,
    ]


# ============================================================================
# Issue Aggregation
# ============================================================================


def get_blocking_issues(all_issues: List[ValidationIssue]) -> List[ValidationIssue]:
    """
    Filter issues to get only blocking ones.

    Args:
        all_issues: List of all validation issues

    Returns:
        List of blocking issues only
    """
    return [issue for issue in all_issues if issue.severity == "blocking"]


def aggregate_validation_issues(
    step_1_issues: List[ValidationIssue],
    step_2_issues: List[ValidationIssue],
    step_3_issues: List[ValidationIssue],
    step_4_issues: List[ValidationIssue],
    step_5_issues: List[ValidationIssue],
    step_6_issues: List[ValidationIssue],
) -> List[ValidationIssue]:
    """
    Aggregate issues from all validation steps.

    Args:
        step_X_issues: Issues from each validation step

    Returns:
        Combined list of all issues
    """
    return (
        step_1_issues
        + step_2_issues
        + step_3_issues
        + step_4_issues
        + step_5_issues
        + step_6_issues
    )


# ============================================================================
# Conversion Helpers
# ============================================================================


def to_legacy_json_format(extraction: FRIExtractionOutput) -> Dict[str, Any]:
    """
    Convert FRIExtractionOutput to original PoC JSON format.

    Use this for backward compatibility with existing systems.

    Args:
        extraction: Validated extraction output

    Returns:
        Dict in original JSON format
    """
    # Build commands dict dynamically
    commands_dict = {}

    if extraction.command_informations.commands:
        for idx, cmd in enumerate(extraction.command_informations.commands, start=1):
            commands_dict[f"command_{idx}"] = {
                "po": cmd.po,
                "lec": cmd.lec,
                "quantity": {
                    "order_quantity": cmd.quantity.order_quantity,
                    "order_carton": cmd.quantity.order_carton,
                    "presented_quantity": cmd.quantity.presented_quantity,
                    "presented_carton": cmd.quantity.presented_carton,
                },
            }

    # Add command_total
    total = extraction.command_informations.command_total
    commands_dict["command_total"] = {
        "po": total.po,
        "lec": total.lec,
        "total_quantity": {
            "total_order_quantity": total.total_quantity.order_quantity,
            "total_order_carton": total.total_quantity.order_carton,
            "total_presented_quantity": total.total_quantity.presented_quantity,
            "total_presented_carton": total.total_quantity.presented_carton,
        },
    }

    # Build defect descriptions for general check
    general_defects = []
    for defect in extraction.aql.general_check.defect_description:
        general_defects.append(
            {
                defect.defect_description: "description",
                "critical": defect.critical,
                "major": defect.major,
                "minor": defect.minor,
            }
        )

    # Build special check if exists
    special_check_dict = None
    if extraction.aql.special_check:
        special_defects = []
        for defect in extraction.aql.special_check.defect_description:
            special_defects.append(
                {
                    defect.defect_description: "description",
                    "critical": defect.critical,
                    "major": defect.major,
                    "minor": defect.minor,
                }
            )

        special_check_dict = {
            "level": extraction.aql.special_check.level.value,
            "sample_size": extraction.aql.special_check.sample_size,
            "category": {
                "critical": extraction.aql.special_check.category.critical,
                "major": extraction.aql.special_check.category.major,
                "minor": extraction.aql.special_check.category.minor,
            },
            "maximum_allowed": {
                "critical": extraction.aql.special_check.maximum_allowed.critical,
                "major": extraction.aql.special_check.maximum_allowed.major,
                "minor": extraction.aql.special_check.maximum_allowed.minor,
            },
            "defect_description": special_defects,
        }

    return {
        "report": {
            "laboratory": extraction.report.laboratory,
            "id_report": extraction.report.id_report,
            "date_report": extraction.report.date_report,
        },
        "barcode": {
            "gtin": extraction.barcode.gtin,
            "export_carton": extraction.barcode.export_carton,
            "format_export_carton": extraction.barcode.format_export_carton,
            "format_packaging": extraction.barcode.format_packaging,
        },
        "product": {
            "product_label": extraction.product.product_label,
            "product_description": extraction.product.product_description,
            "supplier_label": extraction.product.supplier_label,
            "supplier_ref": extraction.product.supplier_ref,
            "manufacturer_label": extraction.product.manufacturer_label,
        },
        "silica_gel": {
            "carton": extraction.silica_gel.carton.value
            if extraction.silica_gel
            else None,
            "quantity": extraction.silica_gel.quantity
            if extraction.silica_gel
            else None,
            "white_transparent": extraction.silica_gel.white_transparent
            if extraction.silica_gel
            else None,
            "name": extraction.silica_gel.name.value if extraction.silica_gel else None,
        }
        if extraction.silica_gel
        else None,
        "command_informations": commands_dict,
        "inspection_conclusion": {
            "style_material": extraction.inspection_conclusion.style_material.value,
            "function_test": extraction.inspection_conclusion.function_test.value,
            "workmanship": extraction.inspection_conclusion.workmanship.value,
            "shipping_mark": extraction.inspection_conclusion.shipping_mark.value,
            "packaging_label": extraction.inspection_conclusion.packaging_label.value,
            "measurement": extraction.inspection_conclusion.measurement.value,
            "barcode_grade": extraction.inspection_conclusion.barcode_grade.value,
        },
        "overall_inspection_conclusion": extraction.overall_inspection_conclusion.value,
        "notes": {
            "nc_remarks": extraction.notes.nc_remarks,
            "informative_remarks": extraction.notes.informative_remarks,
            "notes": extraction.notes.notes,
        },
        "aql": {
            "general_check": {
                "level": extraction.aql.general_check.level.value,
                "sample_size": extraction.aql.general_check.sample_size,
                "no_opened_carton": extraction.aql.general_check.no_opened_carton,
                "category": {
                    "critical": extraction.aql.general_check.category.critical,
                    "major": extraction.aql.general_check.category.major,
                    "minor": extraction.aql.general_check.category.minor,
                },
                "maximum_allowed": {
                    "critical": extraction.aql.general_check.maximum_allowed.critical,
                    "major": extraction.aql.general_check.maximum_allowed.major,
                    "minor": extraction.aql.general_check.maximum_allowed.minor,
                },
                "defect_description": general_defects,
            },
            "special_check": special_check_dict,
        },
        "shipping_marks": {
            "barcode_conformity_inner_carton": extraction.shipping_marks.barcode_conformity_inner_carton,
            "barcode_conformity_master_carton": extraction.shipping_marks.barcode_conformity_master_carton,
        },
    }
