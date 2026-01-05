"""
Example usage of FRI Pydantic models for extraction and validation.

This file demonstrates how to use the models in a real workflow.
"""

from helpers.fri_helpers import (
    check_ean_format,
    check_gtin_grade,
    check_quantity_match,
    check_silica_gel_conformity,
    determine_verdict_type,
    get_blocking_issues,
    requires_human_verification,
)
from models.fri import (
    FRIAQL,
    AQLLevel,
    FRIAnalysisValidation,
    FRIAQLCategory,
    FRIAQLMaximumAllowed,
    FRIBarcode,
    FRICommand,
    FRICommandInformations,
    FRICommandTotal,
    FRIDefect,
    # Extraction models
    FRIExtractionOutput,
    FRIFinalVerdict,
    FRIGeneralCheck,
    FRIInspectionConclusion,
    FRINotes,
    FRIProduct,
    FRIQuantity,
    FRIReportInfo,
    FRIShippingMarks,
    FRISilicaGel,
    FRISpecialCheck,
    # Validation models
    FRIValidationOutput,
    # Enums
    InspectionResult,
    SilicaGelLocation,
    SilicaGelType,
    SpecialAQLLevel,
    ValidationIssue,
    ValidationStepResult,
    VerdictType,
)


def example_1_simple_extraction():
    """
    Example 1: Create a simple FRI extraction output.
    """
    print("=" * 80)
    print("Example 1: Simple FRI Extraction")
    print("=" * 80)

    # Create extraction output step by step
    extraction = FRIExtractionOutput(
        report=FRIReportInfo(
            laboratory="Bureau Veritas",
            id_report="BV2024-12345A",
            date_report="2024-12-15",
        ),
        barcode=FRIBarcode(
            gtin="3256540123456-A",  # Grade A = PASS
            export_carton="00325654012345612345678901",
            format_export_carton="EAN-128",
            format_packaging="EAN-13",
        ),
        product=FRIProduct(
            product_label="Cotton T-Shirt",
            product_description="100% Cotton, Short Sleeve",
            supplier_label="Textile Supplier Co.",
            supplier_ref="TS-2024-001",
            manufacturer_label="Global Textiles Ltd.",
        ),
        silica_gel=FRISilicaGel(
            carton=SilicaGelLocation.EXPORT,
            quantity=2,
            white_transparent=True,
            name=SilicaGelType.SILICA_GEL,
        ),
        command_informations=FRICommandInformations(
            commands=None,  # Single order, so only command_total
            command_total=FRICommandTotal(
                po="PO-2024-001",
                lec="LEC-123456",
                total_quantity=FRIQuantity(
                    order_quantity=5000,
                    order_carton=100,
                    presented_quantity=5000,
                    presented_carton=100,
                ),
            ),
        ),
        inspection_conclusion=FRIInspectionConclusion(
            style_material=InspectionResult.PASS,
            function_test=InspectionResult.PASS,
            workmanship=InspectionResult.PASS,
            shipping_mark=InspectionResult.PASS,
            packaging_label=InspectionResult.PASS,
            measurement=InspectionResult.PASS,
            barcode_grade=InspectionResult.PASS,
        ),
        overall_inspection_conclusion=InspectionResult.PASS,
        notes=FRINotes(
            nc_remarks=[],
            informative_remarks=["Product quality is excellent"],
            notes=["Inspection completed without issues"],
        ),
        aql=FRIAQL(
            general_check=FRIGeneralCheck(
                level=AQLLevel.II,
                sample_size=80,
                no_opened_carton=8,
                category=FRIAQLCategory(critical=0, major=2.5, minor=4.0),
                maximum_allowed=FRIAQLMaximumAllowed(critical=0, major=5, minor=10),
                defect_description=[],  # No defects found
            ),
            special_check=None,
        ),
        shipping_marks=FRIShippingMarks(
            barcode_conformity_inner_carton="Conformant",
            barcode_conformity_master_carton="Conformant on 4 faces",
        ),
    )

    print(f"✓ Extraction created successfully")
    print(f"  Laboratory: {extraction.report.laboratory}")
    print(f"  Report ID: {extraction.report.id_report}")
    print(f"  Overall Result: {extraction.overall_inspection_conclusion.value}")
    print(f"  Product: {extraction.product.product_label}")
    print()


def example_2_extraction_with_multiple_commands():
    """
    Example 2: Extraction with multiple commands.
    """
    print("=" * 80)
    print("Example 2: Multiple Commands")
    print("=" * 80)

    extraction = FRIExtractionOutput(
        report=FRIReportInfo(
            laboratory="SGS", id_report="SGS-2024-ABC", date_report="2024-12-20"
        ),
        barcode=FRIBarcode(
            gtin="9876543210123-B",
            export_carton="00987654321012345678901234",
            format_export_carton="EAN-128",
            format_packaging="EAN-13",
        ),
        product=FRIProduct(
            product_label="Ceramic Mug",
            product_description="White ceramic, 350ml capacity",
            supplier_label="Ceramics R Us",
            supplier_ref="CRU-MUG-001",
            manufacturer_label="China Ceramics Factory",
        ),
        silica_gel=None,  # Not applicable for ceramic products
        command_informations=FRICommandInformations(
            commands=[
                FRICommand(
                    po="PO-2024-100",
                    lec="LEC-100001",
                    quantity=FRIQuantity(
                        order_quantity=3000,
                        order_carton=60,
                        presented_quantity=3000,
                        presented_carton=60,
                    ),
                ),
                FRICommand(
                    po="PO-2024-101",
                    lec="LEC-100002",
                    quantity=FRIQuantity(
                        order_quantity=2000,
                        order_carton=40,
                        presented_quantity=2000,
                        presented_carton=40,
                    ),
                ),
            ],
            command_total=FRICommandTotal(
                po=None,  # Multiple POs
                lec=None,  # Multiple LECs
                total_quantity=FRIQuantity(
                    order_quantity=5000,
                    order_carton=100,
                    presented_quantity=5000,
                    presented_carton=100,
                ),
            ),
        ),
        inspection_conclusion=FRIInspectionConclusion(
            style_material=InspectionResult.PASS,
            function_test=InspectionResult.PASS,
            workmanship=InspectionResult.PASS,
            shipping_mark=InspectionResult.PASS,
            packaging_label=InspectionResult.PASS,
            measurement=InspectionResult.PASS,
            barcode_grade=InspectionResult.PASS,
        ),
        overall_inspection_conclusion=InspectionResult.PASS,
        notes=FRINotes(),
        aql=FRIAQL(
            general_check=FRIGeneralCheck(
                level=AQLLevel.II,
                sample_size=125,
                no_opened_carton=10,
                category=FRIAQLCategory(critical=0, major=2.5, minor=4.0),
                maximum_allowed=FRIAQLMaximumAllowed(critical=0, major=7, minor=14),
                defect_description=[],
            )
        ),
        shipping_marks=FRIShippingMarks(
            barcode_conformity_inner_carton="OK",
            barcode_conformity_master_carton="OK - 4 faces",
        ),
    )

    print(f"✓ Extraction with multiple commands created")
    print(f"  Number of commands: {len(extraction.command_informations.commands)}")
    for idx, cmd in enumerate(extraction.command_informations.commands, 1):
        print(f"  Command {idx}: PO={cmd.po}, Quantity={cmd.quantity.order_quantity}")
    print(
        f"  Total quantity: {extraction.command_informations.command_total.total_quantity.order_quantity}"
    )
    print()


def example_3_validation_with_issues():
    """
    Example 3: Complete validation workflow with issues detected.
    """
    print("=" * 80)
    print("Example 3: Validation with Issues")
    print("=" * 80)

    # First, create extraction (with some issues)
    extraction = FRIExtractionOutput(
        report=FRIReportInfo(
            laboratory="TUV", id_report="TUV-2024-999", date_report="2024-12-10"
        ),
        barcode=FRIBarcode(
            gtin="1234567890123-D",  # Grade D = FAIL
            export_carton="00123456789012345678901234",
            format_export_carton="Code-39",  # Wrong format!
            format_packaging="EAN-13",
        ),
        product=FRIProduct(
            product_label="Plastic Container",
            product_description="Food storage, 1L",
            supplier_label="Plastics Inc.",
            supplier_ref="PI-CONT-001",
            manufacturer_label="Vietnam Plastics",
        ),
        silica_gel=FRISilicaGel(
            carton=SilicaGelLocation.EXPORT,
            quantity=1,
            white_transparent=False,  # Non-conformant!
            name=SilicaGelType.SILICA_GEL,
        ),
        command_informations=FRICommandInformations(
            command_total=FRICommandTotal(
                po="PO-2024-500",
                lec="LEC-500000",
                total_quantity=FRIQuantity(
                    order_quantity=10000,
                    order_carton=200,
                    presented_quantity=9500,  # Quantity mismatch!
                    presented_carton=190,
                ),
            )
        ),
        inspection_conclusion=FRIInspectionConclusion(
            style_material=InspectionResult.PASS,
            function_test=InspectionResult.PASS,
            workmanship=InspectionResult.FAIL,  # One failure
            shipping_mark=InspectionResult.PASS,
            packaging_label=InspectionResult.PASS,
            measurement=InspectionResult.PASS,
            barcode_grade=InspectionResult.PASS,
        ),
        overall_inspection_conclusion=InspectionResult.PASS,  # Lab says PASS
        notes=FRINotes(nc_remarks=["Minor workmanship issues on 3 samples"]),
        aql=FRIAQL(
            general_check=FRIGeneralCheck(
                level=AQLLevel.II,
                sample_size=200,
                no_opened_carton=15,
                category=FRIAQLCategory(critical=0, major=2.5, minor=4.0),
                maximum_allowed=FRIAQLMaximumAllowed(critical=0, major=10, minor=21),
                defect_description=[
                    FRIDefect(
                        defect_description="Surface scratches",
                        critical=0,
                        major=15,  # Exceeds AC of 10!
                        minor=5,
                    )
                ],
            )
        ),
        shipping_marks=FRIShippingMarks(
            barcode_conformity_inner_carton="OK",
            barcode_conformity_master_carton="Only 2 faces marked",  # Non-conformant!
        ),
    )

    # Create validation issues
    issues = [
        ValidationIssue(
            step="Step 2: General Information",
            severity="blocking",
            field="barcode.format_export_carton",
            message="Export carton format is Code-39, must be EAN-128",
            lab_value="Code-39",
            expected_value="EAN-128",
        ),
        ValidationIssue(
            step="Step 2: General Information",
            severity="blocking",
            field="barcode.gtin",
            message="GTIN grade is D, must be A or B for PASS",
            lab_value="D",
            expected_value="A or B",
        ),
        ValidationIssue(
            step="Step 2: General Information",
            severity="blocking",
            field="silica_gel.white_transparent",
            message="Silica gel is not white or transparent",
            lab_value="False",
            expected_value="True",
        ),
        ValidationIssue(
            step="Step 2: General Information",
            severity="blocking",
            field="shipping_marks.barcode_conformity_master_carton",
            message="Gencode must be on 4 main faces, only 2 marked",
            lab_value="Only 2 faces marked",
            expected_value="4 faces marked",
        ),
        ValidationIssue(
            step="Step 3: Quantity",
            severity="blocking",
            field="command_informations.command_total.total_quantity",
            message="Quantity mismatch: ordered 10000, presented 9500",
            lab_value="9500",
            expected_value="10000",
        ),
        ValidationIssue(
            step="Step 4: Inspection Conclusion",
            severity="warning",
            field="inspection_conclusion.workmanship",
            message="Workmanship marked as FAIL",
            lab_value="fail",
            expected_value="pass",
        ),
        ValidationIssue(
            step="Step 5: AQL",
            severity="blocking",
            field="aql.general_check.defect_description",
            message="Major defects (15) exceed AC limit (10)",
            lab_value="15",
            expected_value="≤ 10",
        ),
    ]

    # Create validation step results
    step_results = {
        "step_1": ValidationStepResult(
            step_name="Step 1: Remarks Analysis",
            result=InspectionResult.PASS,
            issues=[],
            remarks="No blocking remarks identified",
        ),
        "step_2": ValidationStepResult(
            step_name="Step 2: General Information",
            result=InspectionResult.FAIL,
            issues=[i for i in issues if "Step 2" in i.step],
            remarks="Multiple barcode and silica gel non-conformities",
        ),
        "step_3": ValidationStepResult(
            step_name="Step 3: Quantity",
            result=InspectionResult.FAIL,
            issues=[i for i in issues if "Step 3" in i.step],
            remarks="Quantity mismatch detected",
        ),
        "step_4": ValidationStepResult(
            step_name="Step 4: Inspection Conclusion",
            result=InspectionResult.FAIL,
            issues=[i for i in issues if "Step 4" in i.step],
            remarks="Workmanship failure noted",
        ),
        "step_5": ValidationStepResult(
            step_name="Step 5: AQL",
            result=InspectionResult.FAIL,
            issues=[i for i in issues if "Step 5" in i.step],
            remarks="Major defects exceed acceptable limits",
        ),
        "step_6": ValidationStepResult(
            step_name="Step 6: Decision",
            result=InspectionResult.FAIL,
            issues=[],
            remarks="Multiple blocking issues result in FAIL",
        ),
    }

    # Create analysis validation
    analysis = FRIAnalysisValidation(
        step_1_remarks_analysis=step_results["step_1"],
        step_2_general_info=step_results["step_2"],
        step_3_quantity=step_results["step_3"],
        step_4_inspection_conclusion=step_results["step_4"],
        step_5_aql=step_results["step_5"],
        step_6_decision=step_results["step_6"],
        all_issues=issues,
        siplec_result=InspectionResult.FAIL,
    )

    # Determine verdict
    verdict_type = determine_verdict_type(
        extraction.overall_inspection_conclusion, analysis.siplec_result
    )

    # Create final verdict
    verdict = FRIFinalVerdict(
        lab_result=extraction.overall_inspection_conclusion,
        siplec_result=analysis.siplec_result,
        verdict_type=verdict_type,
        requires_human_verification=requires_human_verification(verdict_type),
        verdict_message=(
            f"Laboratory reported PASS, but SIPLEC validation identified {len(issues)} issues "
            f"including {len(get_blocking_issues(issues))} blocking issues. "
            f"Result: FAIL. Manual review required due to discrepancy."
        ),
        blocking_issues=get_blocking_issues(issues),
    )

    # Create complete validation output
    validation_output = FRIValidationOutput(
        part_1_extraction=extraction, part_2_analysis=analysis, part_3_verdict=verdict
    )

    print(f"✓ Complete validation created")
    print(f"  Lab Result: {verdict.lab_result.value}")
    print(f"  SIPLEC Result: {verdict.siplec_result.value}")
    print(f"  Verdict Type: {verdict.verdict_type.value}")
    print(f"  Requires Human Review: {verdict.requires_human_verification}")
    print(f"  Total Issues: {len(issues)}")
    print(f"  Blocking Issues: {len(verdict.blocking_issues)}")
    print()
    print("Blocking Issues:")
    for issue in verdict.blocking_issues:
        print(f"  - [{issue.step}] {issue.field}: {issue.message}")
    print()


def example_4_json_serialization():
    """
    Example 4: JSON serialization and schema generation.
    """
    print("=" * 80)
    print("Example 4: JSON Serialization")
    print("=" * 80)

    # Create simple extraction
    extraction = FRIExtractionOutput(
        report=FRIReportInfo(
            laboratory="Test Lab", id_report="TEST-001", date_report="2024-01-01"
        ),
        barcode=FRIBarcode(
            gtin="1111111111111-A",
            export_carton="001111111111111111111111111",
            format_export_carton="EAN-128",
            format_packaging="EAN-13",
        ),
        product=FRIProduct(
            product_label="Test Product",
            product_description="Test",
            supplier_label="Test Supplier",
            supplier_ref="TEST-REF",
            manufacturer_label="Test Manufacturer",
        ),
        silica_gel=None,
        command_informations=FRICommandInformations(
            command_total=FRICommandTotal(
                po="TEST-PO",
                lec="TEST-LEC",
                total_quantity=FRIQuantity(
                    order_quantity=100,
                    order_carton=10,
                    presented_quantity=100,
                    presented_carton=10,
                ),
            )
        ),
        inspection_conclusion=FRIInspectionConclusion(
            style_material=InspectionResult.PASS,
            function_test=InspectionResult.PASS,
            workmanship=InspectionResult.PASS,
            shipping_mark=InspectionResult.PASS,
            packaging_label=InspectionResult.PASS,
            measurement=InspectionResult.PASS,
            barcode_grade=InspectionResult.PASS,
        ),
        overall_inspection_conclusion=InspectionResult.PASS,
        notes=FRINotes(),
        aql=FRIAQL(
            general_check=FRIGeneralCheck(
                level=AQLLevel.II,
                sample_size=13,
                no_opened_carton=2,
                category=FRIAQLCategory(critical=0, major=2.5, minor=4.0),
                maximum_allowed=FRIAQLMaximumAllowed(critical=0, major=1, minor=2),
                defect_description=[],
            )
        ),
        shipping_marks=FRIShippingMarks(
            barcode_conformity_inner_carton="OK",
            barcode_conformity_master_carton="OK - 4 faces",
        ),
    )

    # Serialize to JSON
    json_str = extraction.model_dump_json(indent=2)
    print("✓ JSON serialization successful")
    print(f"  JSON length: {len(json_str)} characters")

    # Get schema
    schema = FRIExtractionOutput.model_json_schema()
    print(f"  Schema properties: {len(schema['properties'])} top-level fields")
    print()

    # Show first 500 characters of JSON
    print("JSON Preview (first 500 chars):")
    print(json_str[:500] + "...")
    print()


def main():
    """Run all examples."""
    example_1_simple_extraction()
    example_2_extraction_with_multiple_commands()
    example_3_validation_with_issues()
    example_4_json_serialization()

    print("=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
