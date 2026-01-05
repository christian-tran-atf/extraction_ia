# FRI Pydantic Models - Quick Start Guide

## Overview

This implementation provides production-ready Pydantic models for extracting and validating Final Random Inspection (FRI) quality reports. The models transform your PoC prompt-based JSON into type-safe, validated Python classes.

## Installation

No additional dependencies required beyond what's already in your project:
- `pydantic` (already installed)

## Quick Start

### 1. Import the Models

```python
from src.models import (
    FRIExtractionOutput,
    FRIValidationOutput,
    InspectionResult,
    VerdictType,
)
```

### 2. Use with LLM for Extraction

```python
# Get JSON schema for LLM
from src.fri_helpers import get_extraction_schema

schema = get_extraction_schema()

# Pass schema to your LLM prompt
llm_prompt = f"""
Extract FRI report data according to this schema:
{schema}

[... your extraction prompt ...]
"""

# Parse and validate LLM response
raw_json = llm_api_call(llm_prompt, pdf_images)
extraction = FRIExtractionOutput.model_validate(raw_json)

# Access typed fields
print(f"Lab: {extraction.report.laboratory}")
print(f"Result: {extraction.overall_inspection_conclusion.value}")
```

### 3. Validate with Business Rules

```python
from src.models import (
    FRIValidationOutput,
    FRIAnalysisValidation,
    ValidationStepResult,
    ValidationIssue,
)

# Build validation analysis
issues = []

# Step 2: Check barcode format
from src.fri_helpers import check_ean_format
if not check_ean_format(extraction.barcode.format_packaging, "EAN-13"):
    issues.append(ValidationIssue(
        step="Step 2: General Information",
        severity="blocking",
        field="barcode.format_packaging",
        message="Packaging format must be EAN-13",
        lab_value=extraction.barcode.format_packaging,
        expected_value="EAN-13"
    ))

# Create complete validation output
validation = FRIValidationOutput(
    part_1_extraction=extraction,
    part_2_analysis=analysis,  # Your validation analysis
    part_3_verdict=verdict      # Your final verdict
)
```

### 4. Generate JSON for Downstream Systems

```python
# Export as JSON
json_output = validation.model_dump_json(indent=2)

# Or convert to legacy format
from src.fri_helpers import to_legacy_json_format
legacy_json = to_legacy_json_format(extraction)
```

## File Structure

```
src/
├── models.py              # All Pydantic models (main file)
├── fri_helpers.py         # Helper functions and utilities
└── prompts/
    └── fri/
        ├── extraction.py  # Extraction prompts (update to use models)
        └── validation.py  # Validation prompts (update to use models)

examples/
└── fri_usage_examples.py  # Complete usage examples

docs/
└── FRI_MODELS_DOCUMENTATION.md  # Comprehensive documentation
```

## Key Features

### Type Safety
All fields are strongly typed with Pydantic validation:
```python
extraction.aql.general_check.level  # Type: AQLLevel enum
extraction.overall_inspection_conclusion  # Type: InspectionResult enum
extraction.command_informations.command_total.total_quantity.order_quantity  # Type: int
```

### Automatic Validation
Pydantic validates on creation:
```python
# ✓ This works
FRIQuantity(order_quantity=100, order_carton=10, ...)

# ✗ This raises ValidationError
FRIQuantity(order_quantity="invalid", ...)  # Must be int
```

### Enums for Categorical Values
```python
InspectionResult.PASS       # "pass"
InspectionResult.FAIL       # "fail"
InspectionResult.IN_WAITING # "in_waiting"

VerdictType.VRAI_PASS   # Lab Pass & SIPLEC Pass
VerdictType.FAUX_PASS   # Lab Pass but SIPLEC Fail
```

### Three-Part Output Structure

**Part 1: Extraction** (`FRIExtractionOutput`)
- Raw data extracted from PDF report
- Matches original JSON schema structure

**Part 2: Analysis** (`FRIAnalysisValidation`)
- 6-step validation per SIPLEC business rules
- Collects all issues found during validation
- Determines SIPLEC's final result

**Part 3: Verdict** (`FRIFinalVerdict`)
- Compares lab result vs SIPLEC result
- Classifies as VRAI_PASS, FAUX_PASS, etc.
- Flags if human verification needed

## Run Examples

```bash
cd /path/to/extraction_ia
source .venv/bin/activate
PYTHONPATH=$PWD python examples/fri_usage_examples.py
```

Output:
```
================================================================================
Example 1: Simple FRI Extraction
================================================================================
✓ Extraction created successfully
  Laboratory: Bureau Veritas
  Report ID: BV2024-12345A
  Overall Result: pass
  Product: Cotton T-Shirt

[... more examples ...]
```

## Integration Checklist

- [ ] **Update extraction prompts** (`src/prompts/fri/extraction.py`)
  - Import `FRIExtractionOutput`
  - Use `model_json_schema()` to generate schema for LLM
  - Validate LLM response with `model_validate()`

- [ ] **Update validation prompts** (`src/prompts/fri/validation.py`)
  - Import validation models
  - Build `ValidationIssue` objects for each check
  - Create complete `FRIValidationOutput`

- [ ] **Update core processing** (`src/core.py`)
  - Replace dict-based processing with Pydantic models
  - Use typed access instead of dict keys
  - Leverage Pydantic's `.model_dump()` for serialization

- [ ] **Add tests**
  - Unit tests for model validation
  - Integration tests for extraction → validation flow
  - Business rule tests using `fri_helpers.py`

## Business Rules Reference

### Critical Validation Rules

**Step 2: General Information**
- ✓ GTIN grade = A or B (C/D/E = FAIL)
- ✓ Packaging format = EAN-13 or variant
- ✓ Export carton format = EAN-128 or variant
- ✓ Gencode on 4 faces of master carton
- ✓ Silica gel: white or transparent
- ✓ Silica gel must be specified (missing = FAIL)

**Step 3: Quantity**
- ✓ Order quantity = Presented quantity
- ✓ Order carton = Presented carton

**Step 4: Inspection Conclusion**
- ✓ All 7 criteria must be PASS
  - style_material, function_test, workmanship
  - shipping_mark, packaging_label, measurement
  - barcode_grade

**Step 5: AQL**
- ✓ Sample size ≥ required size
- ✓ Critical defects ≤ AC (zero tolerance)
- ✓ Major defects ≤ AC
- ✓ Minor defects ≤ AC

### Remark Overrides

Specific remarks can override lab decisions:
- Weight difference: Lab FAIL → SIPLEC PASS
- Unclear markings: Lab IN_WAITING → SIPLEC FAIL
- Wrong product code: Lab IN_WAITING → SIPLEC FAIL
- EAN-128 grade A/B: SIPLEC PASS; C/D/E: SIPLEC FAIL
- Metal staples/nails: SIPLEC PASS
- Excessive empty space: SIPLEC FAIL

See full list in `docs/FRI_MODELS_DOCUMENTATION.md`

## Helper Functions

```python
from src.fri_helpers import (
    check_gtin_grade,
    check_ean_format,
    check_quantity_match,
    check_silica_gel_conformity,
    determine_verdict_type,
    get_blocking_issues,
    to_legacy_json_format,
)

# Check GTIN grade
is_pass, grade = check_gtin_grade("3256540123456-A")
# → (True, 'A')

# Check EAN format
is_valid = check_ean_format("Code 13", "EAN-13")
# → True (accepts variant)

# Determine verdict
verdict = determine_verdict_type(
    lab_result=InspectionResult.PASS,
    siplec_result=InspectionResult.FAIL
)
# → VerdictType.FAUX_PASS
```

## Next Steps

1. **Read full documentation**: `docs/FRI_MODELS_DOCUMENTATION.md`
2. **Study examples**: `examples/fri_usage_examples.py`
3. **Update prompts**: Integrate models into extraction/validation prompts
4. **Add AQL tables**: Create lookup functions for AQL AC/RE values
5. **Build remark parser**: Automated remark analysis and override logic
6. **Add tests**: Unit and integration tests for validation pipeline

## Benefits Over PoC Approach

| PoC (Dict-based) | Production (Pydantic) |
|------------------|----------------------|
| No type checking | Full type safety |
| Manual validation | Automatic validation |
| Dict key access (`data['report']['id_report']`) | Typed access (`extraction.report.id_report`) |
| String values for categories | Enums with autocomplete |
| No IDE support | Full IDE autocomplete |
| Runtime errors | Compile-time errors |
| No schema enforcement | Strict schema validation |

## Support

- **Documentation**: `docs/FRI_MODELS_DOCUMENTATION.md`
- **Examples**: `examples/fri_usage_examples.py`
- **Helpers**: `src/fri_helpers.py`
- **Models**: `src/models.py` (fully documented with docstrings)

## Backup

Original models backed up to: `src/models.py.backup`

---

**Ready to industrialize your FRI report processing! 🚀**
