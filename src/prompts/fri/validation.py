from typing import List, Union

from google.genai import types

prompt = """
You are an expert in validating document summaries.
Your task is to assess whether the provided summary accurately reflects the content of the document.
Please respond with "VALID" if the summary is accurate, or "INVALID" if it is not.

---
Context data:
```json
{extraction_output_json}
```
"""

message: Union[List[types.PartUnionDict], types.PartUnionDict] = []
