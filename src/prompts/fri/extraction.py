from typing import TYPE_CHECKING, List, Union

from google.genai import types

if TYPE_CHECKING:
    from src.config import Settings

additional_instructions_part = ""

# additional_instructions_part = """
# - Dans le fichier JSON que tu complètes, afin de compléter la partie maximum_allowed dans les AQL, base toi sur les éléments présents dans le tableau General / Special AQL que je vais te partager par la suite. Tu pourras remonter l’information si tu ne trouve pas les mêmes valeurs que ce qui est indiqué dans le rapport du laboratoire.
# """

system_instruction = f"""
Tu es un assistant pour des techniciens qualité chez SIPLEC.
Ton objectif est d'extraire des informations depuis des rapports de tests 'Final Random Inspection', fournis sous format PDF.
Dans le prompt, tu pourras trouver une liste d'images annotées pour t'aider dans ta tâche.

Voici quelques indications complémentaires :
- Le numéro de rapport peut contenir des lettres, ne les oublies pas.
- Le code Export carton peut contenir une lettre à la fin qui correspond au Grade. Il faut bien la récupérer même si il y a des des tirets ou qu’elle est entre parenthèses.
- Pour le nom du Silica gel, il faut prendre uniquement l’élément qui est coché.
    Tu auras donc trois possibilités :
    - "Silica Gel"
    - "Dri Caly Micro Pak"
    - "Calcium Chlorid"
- Dans la partie remarque, il ne sera pas toujours indiqué s’il s’agit d’une NC / Remarks / Notes. Si tu ne sais pas où le catégoriser tu le mets dans NC.
{additional_instructions_part}
- Pour les informations de commandes, s’il n’y a qu’une seule ligne tu peux compléter uniquement la partie “command_total” pas besoin de faire “command_1” en plus cela fera un doublon. Tu ne dois compléter command_x uniquement quand il y a plusieurs éléments.
- (image 4) Le résultat transmis par le laboratoire de test n’est pas forcément le même que le résultat conservé par SIPLEC. Un pass peut devenir un fail et inversement.
- (image 5) Les commentaires peuvent influencer le résultat global du test transmis par les laboratoires. Certains critères de non conformité ne sont pas rédhibitoires pour SIPLEC et inversement.
- (image 6, image 7) Il faut récupérer le Level et la taille de l'échantillon associé à l’AQL ainsi que les défauts identifiés par type et criticité. 
"""

image_1_global_info_part = "image 1[informations globales]"
image_2_uvc_quantity_part = "image 2[quantité uvc]"
image_3_inspection_conclusion_part = "image 3[conclusion de l'inspection]"
image_4_global_test_result_part = "image 4[résultat global du test]"
image_5_associated_comments_to_test_part = "image 5[commentaires associés au test]"
image_6_aql_general_check_part = "image 6[contrôle AQL général]"
image_7_aql_special_check_part = "image 7[contrôle AQL spécial]"
image_8_gencode_presence_on_cardboard_box_faces_part = (
    "image 8[présence du gencode sur les faces du carton]"
)

def get_parts_without_pdf(settings: "Settings", image_file_names: List[str]) -> Union[List[types.PartUnionDict], types.PartUnionDict]:
    """Generate extraction parts with images based on settings.
    
    Args:
        settings: Settings instance
        image_file_names: List of image file names to use
    """
    captions_and_images_parts = [
        part
        for pair in zip(
            [
                image_1_global_info_part,
                image_2_uvc_quantity_part,
                image_3_inspection_conclusion_part,
                image_4_global_test_result_part,
                image_5_associated_comments_to_test_part,
                image_6_aql_general_check_part,
                image_7_aql_special_check_part,
                image_8_gencode_presence_on_cardboard_box_faces_part,
            ],
            [
                f"{settings.fri_extraction_images_gcs_prefix}/{file_name}"
                for file_name in image_file_names
            ],
        )
        for part in [
            types.Part.from_text(text=pair[0]),
            types.Part.from_uri(file_uri=pair[1], mime_type="image/png"),
        ]
    ]
    return captions_and_images_parts
