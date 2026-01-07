from typing import List, Union

from google.genai import types

system_instruction = """
Tu es un assistant pour des techniciens qualité chez SIPLEC.
Ton objectif est de valider ou non les résultats de tests 'Final Random Inspection', fournis sous format JSON.
Pour cela, tu devras utiliser des règles de validation métiers ci-dessous :
```json
{business_rules_json}
```
"""

instructions_part = types.Part.from_text(
    text="Voici le résultat de l'extraction au format JSON :"
)

prompt_without_extraction_output: Union[
    List[types.PartUnionDict], types.PartUnionDict
] = instructions_part
