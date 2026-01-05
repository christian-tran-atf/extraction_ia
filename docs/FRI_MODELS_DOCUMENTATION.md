# FRI Pydantic Models Documentation

## Overview

This document describes the comprehensive Pydantic models created for extracting and validating Final Random Inspection (FRI) quality reports. The models transform the PoC prompt-based JSON structure into production-ready, type-safe Python classes.

## Architecture

The models are organized into three main sections:

### 1. **Part 1: Extraction Models** (`FRIExtractionOutput`)
Structured data extraction from PDF reports following the original JSON schema.

### 2. **Part 2: Validation Models** (`FRIAnalysisValidation`)
Business rule validation according to SIPLEC's 6-step validation process.

### 3. **Part 3: Verdict Models** (`FRIFinalVerdict`)
Final decision classification comparing laboratory results with SIPLEC analysis.

---

## Model Hierarchy

```
FRIValidationOutput (Complete Output)
├── part_1_extraction: FRIExtractionOutput
│   ├── report: FRIReportInfo
│   ├── barcode: FRIBarcode
│   ├── product: FRIProduct
│   ├── silica_gel: FRISilicaGel (Optional)
│   ├── command_informations: FRICommandInformations
│   │   ├── commands: List[FRICommand] (Optional)
│   │   └── command_total: FRICommandTotal
│   ├── inspection_conclusion: FRIInspectionConclusion
│   ├── overall_inspection_conclusion: InspectionResult
│   ├── notes: FRINotes
│   ├── aql: FRIAQL
│   │   ├── general_check: FRIGeneralCheck
│   │   └── special_check: FRISpecialCheck (Optional)
│   └── shipping_marks: FRIShippingMarks
│
├── part_2_analysis: FRIAnalysisValidation
│   ├── step_1_remarks_analysis: ValidationStepResult
│   ├── step_2_general_info: ValidationStepResult
│   ├── step_3_quantity: ValidationStepResult
│   ├── step_4_inspection_conclusion: ValidationStepResult
│   ├── step_5_aql: ValidationStepResult
│   ├── step_6_decision: ValidationStepResult
│   ├── all_issues: List[ValidationIssue]
│   └── siplec_result: InspectionResult
│
└── part_3_verdict: FRIFinalVerdict
    ├── lab_result: InspectionResult
    ├── siplec_result: InspectionResult
    ├── verdict_type: VerdictType
    ├── requires_human_verification: bool
    ├── verdict_message: str
    └── blocking_issues: List[ValidationIssue]
```

---

## Enumerations

### `InspectionResult`
Result status for inspections.
- `PASS` - Inspection passed
- `FAIL` - Inspection failed
- `IN_WAITING` - Pending manual verification

### `VerdictType`
Classification of final verdict comparing lab vs SIPLEC results.
- `VRAI_PASS` - True Positive: Lab Pass & SIPLEC Pass
- `VRAI_FAIL` - True Negative: Lab Fail & SIPLEC Fail
- `FAUX_PASS` - False Positive: Lab Pass but SIPLEC Fail
- `FAUX_FAIL` - False Negative: Lab Fail but SIPLEC Pass
- `IN_WAITING_RESOLVED` - Lab In Waiting with SIPLEC decision

### `AQLLevel` / `SpecialAQLLevel`
AQL inspection levels for sampling.
- General: `I`, `II`, `III`
- Special: `S1`, `S2`, `S3`, `S4`

### `SilicaGelType`
Types of desiccant materials.
- `SILICA_GEL` - "Silica Gel"
- `DRI_CLAY` - "Dri Caly Micro Pak"
- `CALCIUM_CHLORIDE` - "Calcium Chlorid"

### `SilicaGelLocation`
Packaging location for silica gel.
- `EXPORT`, `INNER`, `PACKAGE`

---

## Key Models Details

### Part 1: Extraction Models

#### `FRIReportInfo`
Basic report metadata.
```python
{
    "laboratory": str,      # Lab name
    "id_report": str,       # Report ID (can contain letters)
    "date_report": str      # Report date
}
```

#### `FRIBarcode`
Barcode and GTIN information with validation rules.
```python
{
    "gtin": str,                    # GTIN with grade letter (A/B for pass)
    "export_carton": str,           # Export carton code
    "format_export_carton": str,    # Must be EAN-128 or variant
    "format_packaging": str         # Must be EAN-13 or variant
}
```

**Business Rules:**
- GTIN grade must be A or B for PASS
- Export carton format must be EAN-128
- Packaging format must be EAN-13

#### `FRISilicaGel`
Moisture control desiccant information.
```python
{
    "carton": SilicaGelLocation,    # Location in packaging
    "quantity": int,                # Number of packets
    "white_transparent": bool,      # SIPLEC requires white or transparent
    "name": SilicaGelType           # Type of desiccant
}
```

**Business Rules:**
- Must be white or transparent (SIPLEC requirement)
- Missing silica gel information = FAIL

#### `FRICommandInformations`
Order and quantity information with intelligent structure.
```python
{
    "commands": Optional[List[FRICommand]],  # Only when multiple orders exist
    "command_total": FRICommandTotal         # Total across all orders
}
```

**Business Rules:**
- Single order: Only populate `command_total`
- Multiple orders: Populate both `commands` list and `command_total`

#### `FRIQuantity`
Quantity tracking with validation hooks.
```python
{
    "order_quantity": int,      # Ordered product quantity
    "order_carton": int,        # Ordered carton quantity
    "presented_quantity": int,  # Received product quantity
    "presented_carton": int     # Received carton quantity
}
```

**Business Rules:**
- `order_quantity` must equal `presented_quantity` for PASS
- `order_carton` must equal `presented_carton` for PASS

#### `FRIInspectionConclusion`
Seven mandatory inspection criteria.
```python
{
    "style_material": InspectionResult,   # Style, material & color
    "function_test": InspectionResult,    # Function test
    "workmanship": InspectionResult,      # Workmanship quality
    "shipping_mark": InspectionResult,    # Shipping mark
    "packaging_label": InspectionResult,  # Packaging/Label
    "measurement": InspectionResult,      # Data measurement
    "barcode_grade": InspectionResult     # Barcode grade
}
```

**Business Rules:**
- All 7 fields must be PASS for overall PASS
- Check remarks for context if any field is FAIL

#### `FRIAQL`
AQL (Acceptable Quality Limit) inspection data.
```python
{
    "general_check": FRIGeneralCheck,
    "special_check": Optional[FRISpecialCheck]
}
```

**AQL Components:**
- `level`: Inspection level (I/II/III or S1-S4)
- `sample_size`: Number of items inspected
- `category`: AQL values (Critical: 0, Major: 1.5/2.5, Minor: 4.0)
- `maximum_allowed`: AC values from AQL tables
- `defect_description`: List of identified defects

**Business Rules:**
- Sample size must be ≥ required size from AQL tables
- Defects must be ≤ AC (Accept) values
- Critical defects AQL = 0 (zero tolerance)
- Major defects AQL = 1.5 or 2.5
- Minor defects AQL = 4.0

---

### Part 2: Validation Models

#### `ValidationIssue`
Individual issue found during validation.
```python
{
    "step": str,                    # Validation step (Step 1-6)
    "severity": "blocking"|"warning"|"info",
    "field": str,                   # Field with issue
    "message": str,                 # Issue description
    "lab_value": Optional[str],     # Lab's value
    "expected_value": Optional[str] # Expected per SIPLEC rules
}
```

#### `ValidationStepResult`
Result of each validation step.
```python
{
    "step_name": str,
    "result": InspectionResult,
    "issues": List[ValidationIssue],
    "remarks": Optional[str]
}
```

#### `FRIAnalysisValidation`
Complete 6-step validation analysis.
```python
{
    "step_1_remarks_analysis": ValidationStepResult,
    "step_2_general_info": ValidationStepResult,
    "step_3_quantity": ValidationStepResult,
    "step_4_inspection_conclusion": ValidationStepResult,
    "step_5_aql": ValidationStepResult,
    "step_6_decision": ValidationStepResult,
    "all_issues": List[ValidationIssue],
    "siplec_result": InspectionResult
}
```

**Validation Steps:**
1. **Remarks Analysis**: Parse remarks for SIPLEC-specific overrides
2. **General Info**: Validate gencode, EAN formats, silica gel
3. **Quantity**: Verify order vs. presented quantities match
4. **Inspection Conclusion**: Check all 7 criteria
5. **AQL**: Validate sample sizes and defect counts
6. **Decision**: Aggregate all results for final SIPLEC decision

---

### Part 3: Verdict Models

#### `FRIFinalVerdict`
Final comparison and classification.
```python
{
    "lab_result": InspectionResult,
    "siplec_result": InspectionResult,
    "verdict_type": VerdictType,
    "requires_human_verification": bool,
    "verdict_message": str,
    "blocking_issues": List[ValidationIssue]
}
```

**Verdict Logic:**
- Lab PASS + SIPLEC PASS → `VRAI_PASS`
- Lab FAIL + SIPLEC FAIL → `VRAI_FAIL`
- Lab PASS + SIPLEC FAIL → `FAUX_PASS` (requires review)
- Lab FAIL + SIPLEC PASS → `FAUX_FAIL` (requires review)
- Lab IN_WAITING → `IN_WAITING_RESOLVED` (SIPLEC decides)

---

## Critical Business Rules Summary

### Step 1: Remarks Analysis
Specific remarks that override lab decisions:
- Weight differences: Lab FAIL → SIPLEC PASS
- Unclear markings: Lab IN_WAITING → SIPLEC FAIL
- Wrong product code: Lab IN_WAITING → SIPLEC FAIL
- Carton size issues: Lab IN_WAITING → SIPLEC PASS
- EAN-128 on 2 non-consecutive faces: Lab note → SIPLEC FAIL
- Tight adhesive tape: Lab IN_WAITING → SIPLEC PASS
- Mold on pallet: Lab not always FAIL → SIPLEC FAIL
- Missing/non-conforming LEC: Lab IN_WAITING → SIPLEC FAIL
- Metal staples/nails: SIPLEC PASS
- Excessive empty space in carton: SIPLEC FAIL
- EAN-128 grade A or B: SIPLEC PASS; C/D/E: SIPLEC FAIL

### Step 2: General Information
- Gencode must be on 4 main faces of master carton
- Packaging must be EAN-13 (or variant)
- Export carton must be EAN-128 (or variant)
- GTIN grade must be A or B
- Silica gel must be white or transparent
- Missing silica gel = FAIL

### Step 3: Quantity
- Order quantity = Presented quantity
- Order carton = Presented carton

### Step 4: Inspection Conclusion
- All 7 criteria must be PASS
- Check remarks if any criterion is FAIL (may override)

### Step 5: AQL
- Sample size ≥ required size from tables
- Critical defects ≤ AC (zero tolerance)
- Major defects ≤ AC
- Minor defects ≤ AC

### Step 6: Decision
- PASS only if ALL steps are PASS
- Any blocking issue → FAIL

---

## Usage Examples

### Example 1: Creating Extraction Output
```python
from src.models import FRIExtractionOutput, FRIReportInfo, FRIBarcode, InspectionResult

extraction_output = FRIExtractionOutput(
    report=FRIReportInfo(
        laboratory="Bureau Veritas",
        id_report="BV2024-12345A",
        date_report="2024-12-15"
    ),
    barcode=FRIBarcode(
        gtin="3256540123456-A",
        export_carton="00325654012345612345678901",
        format_export_carton="EAN-128",
        format_packaging="EAN-13"
    ),
    # ... other fields
    overall_inspection_conclusion=InspectionResult.PASS
)
```

### Example 2: Validation with Issues
```python
from src.models import ValidationIssue, ValidationStepResult, InspectionResult

issue = ValidationIssue(
    step="Step 2: General Information",
    severity="blocking",
    field="barcode.format_packaging",
    message="Packaging format is Code-39, expected EAN-13",
    lab_value="Code-39",
    expected_value="EAN-13"
)

step_result = ValidationStepResult(
    step_name="Step 2: General Information",
    result=InspectionResult.FAIL,
    issues=[issue],
    remarks="Barcode format non-conformity detected"
)
```

### Example 3: Final Verdict
```python
from src.models import FRIFinalVerdict, VerdictType, InspectionResult

verdict = FRIFinalVerdict(
    lab_result=InspectionResult.PASS,
    siplec_result=InspectionResult.FAIL,
    verdict_type=VerdictType.FAUX_PASS,
    requires_human_verification=True,
    verdict_message="Laboratory marked as PASS, but SIPLEC identified EAN-13 format non-conformity. Manual review required.",
    blocking_issues=[issue]
)
```

---

## Integration with Existing Code

### Update Prompt Files
The extraction and validation prompts should now reference these Pydantic models:

```python
# src/prompts/fri/extraction.py
from src.models import FRIExtractionOutput

# Use model.model_json_schema() to generate JSON schema for LLM
extraction_schema = FRIExtractionOutput.model_json_schema()
```

### Validate LLM Output
```python
# Parse and validate LLM JSON response
raw_json = llm_response.get("extraction_data")
validated_extraction = FRIExtractionOutput.model_validate(raw_json)

# Access typed fields
report_id = validated_extraction.report.id_report
lab_name = validated_extraction.report.laboratory
```

### Generate JSON for Validation Prompts
```python
# Convert to JSON for validation prompts
extraction_json = validated_extraction.model_dump_json(indent=2)
```

---

## Validation Features

### Automatic Validation
Pydantic automatically validates:
- Type correctness (str, int, bool, enums)
- Required fields vs. optional fields
- Constraints (e.g., `sample_size > 0`, `critical >= 0`)
- Enum membership (e.g., AQLLevel must be I, II, or III)

### Custom Validators
- `FRIBarcode.validate_gtin_grade`: Ensures GTIN is not empty
- `FRIQuantity.check_quantity_match`: Flags quantity mismatches (note: doesn't raise error)

### Field Constraints
- `sample_size: int = Field(..., gt=0)` - Must be > 0
- `critical: int = Field(0, ge=0)` - Must be ≥ 0
- `white_transparent: bool` - Must be boolean

---

## Future Enhancements

1. **Additional Validators**: Implement validators for:
   - EAN-13/EAN-128 format checking
   - GTIN grade extraction and validation
   - LEC number format validation

2. **AQL Table Integration**: Create helper functions to:
   - Lookup AC/RE values from AQL tables
   - Automatically populate `maximum_allowed` fields

3. **Remark Parser**: Build a remark analysis engine to:
   - Automatically classify remarks into categories
   - Apply business rule overrides
   - Generate validation issues

4. **Report Generation**: Use models to:
   - Generate PDF/HTML validation reports
   - Export to Excel for analysis
   - Integrate with BI dashboards

---

## Migration from PoC

### Changes from Original JSON Schema

1. **Nested Structure**: Flat JSON → Hierarchical Pydantic models
2. **Type Safety**: Strings → Enums for categorical values
3. **Validation**: No validation → Automatic + custom validators
4. **Commands**: Dynamic keys (`command_1`, `command_2`) → List structure
5. **Three-Part Output**: Separate models for extraction, analysis, and verdict

### Backward Compatibility
To maintain compatibility with existing code expecting the original JSON format:

```python
# Convert Pydantic model to original JSON structure
def to_legacy_format(output: FRIValidationOutput) -> dict:
    extraction = output.part_1_extraction
    
    # Map to original format
    return {
        "report": {
            "laboratory": extraction.report.laboratory,
            "id_report": extraction.report.id_report,
            "date_report": extraction.report.date_report
        },
        # ... continue mapping
    }
```

---

## Testing

```python
import pytest
from src.models import FRIExtractionOutput, InspectionResult

def test_valid_extraction():
    """Test valid FRI extraction data."""
    data = {
        "report": {"laboratory": "BV", "id_report": "123", "date_report": "2024-01-01"},
        # ... complete valid data
    }
    output = FRIExtractionOutput.model_validate(data)
    assert output.report.laboratory == "BV"

def test_invalid_inspection_result():
    """Test invalid inspection result enum."""
    with pytest.raises(ValueError):
        InspectionResult("invalid")
```

---

## Conclusion

These Pydantic models provide a production-ready, type-safe foundation for industrializing the FRI report extraction and validation process. They enforce business rules at the data structure level, provide clear documentation, and enable robust validation of LLM outputs.

The models follow the exact structure specified in the original prompt while adding type safety, validation, and maintainability improvements essential for production systems.
