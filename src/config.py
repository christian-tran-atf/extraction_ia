"""Configuration settings for the extraction and validation process."""

from functools import cached_property
from typing import List, Type, Union

from google.genai import types
from pydantic import BaseModel, Field, computed_field
from pydantic_settings import (
    BaseSettings,
    # GoogleSecretManagerSettingsSource,
    # PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from models.fri import (
    ExtractionOutput,
    FRIExtractionOutput,
    FRIValidationOutput,
    ValidationOutput,
)
from src.prompts.fri.extraction import prompt_without_pdf as fri_extraction_prompt
from src.prompts.fri.validation import prompt as fri_validation_prompt


class ExtractionDocument(BaseModel):
    extraction_prompt: Union[
        Union[List[types.PartUnionDict], types.PartUnionDict],
        Union[types.ContentListUnion, types.ContentListUnionDict],
    ] = Field(..., description="The prompt template for extraction.")
    extraction_output_schema_model: Type[ExtractionOutput] = Field(
        ..., description="The schema model for the extraction output."
    )
    extraction_images_gcs_file_names: list[str] = Field(
        default=[],
        description="The list of GCS file names for extraction helper images.",
    )


class ValidationDocument(ExtractionDocument):
    validation_prompt: Union[
        Union[List[types.PartUnionDict], types.PartUnionDict],
        Union[types.ContentListUnion, types.ContentListUnionDict],
    ] = Field(..., description="The prompt template for validation.")
    validation_output_schema_model: Type[ValidationOutput] = Field(
        ..., description="The schema model for the validation output."
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    # model_config = SettingsConfigDict(env_nested_delimiter="__")

    # secret_name: str = "secret-cr-extraction-ia-"
    logger_name: str = "cr-extraction-ia"

    # BigQuery settings
    # Source table
    bigquery_source_node_name: str = "sbx-se"
    bigquery_source_dataset_name: str = "test_christian_tran_leclerc"
    bigquery_source_table_name: str = "controle_extraction_ia"
    pending_status: str = "PENDING"
    error_status: str = "ERROR"
    attempts_limit: int = 3
    # Destination table
    bigquery_destination_node_name: str = "sbx-se"
    bigquery_destination_dataset_name: str = "test_christian_tran_leclerc"
    bigquery_destination_table_name: str = "resultats_extraction_ia"

    # Cloud Storage settings
    gcs_bucket_name: str = "sbx-se-christian-tran-leclerc"
    gcs_images_folder_name: str = "images"
    gcs_images_extraction_folder_name: str = "extraction"
    gcs_images_validation_folder_name: str = "validation"

    # Document processing settings
    llm_model_id: str = "gemini-2.5-pro"
    extraction_semaphore_limit: int = 20
    # extraction_llm_model_id: str = "gemini-2.5-pro"
    validation_semaphore_limit: int = 20
    # validation_llm_model_id: str = "gemini-2.5-pro"

    document_config: dict[str, ExtractionDocument | ValidationDocument] = {
        "FRI": ValidationDocument(
            extraction_prompt=fri_extraction_prompt,
            extraction_output_schema_model=FRIExtractionOutput,
            extraction_images_gcs_file_names=[
                "image_1_global_information.png",
                "image_2_uvc_quantity.png",
                "image_3_inspection_conclusion.png",
                "image_4_global_test_result.png",
                "image_5_associated_comments_to_test.png",
                "image_6_aql_general_check.png",
                "image_7_aql_special_check.png",
                "image_8_gencode_presence_on_cardboard_box_faces.png",
            ],
            validation_prompt=fri_validation_prompt,
            validation_output_schema_model=FRIValidationOutput,
        )
    }

    @computed_field
    @cached_property
    def fri_extraction_images_gcs_prefix(self) -> str:
        return f"gs://{self.gcs_bucket_name}/{self.gcs_images_folder_name}/fri/{self.gcs_images_extraction_folder_name}"

    # @classmethod
    # def settings_customise_sources(
    #     cls,
    #     settings_cls: type[BaseSettings],
    #     init_settings: PydanticBaseSettingsSource,
    #     env_settings: PydanticBaseSettingsSource,
    #     dotenv_settings: PydanticBaseSettingsSource,
    #     file_secret_settings: PydanticBaseSettingsSource,
    # ) -> tuple[PydanticBaseSettingsSource, ...]:
    #     gcp_settings = GoogleSecretManagerSettingsSource(
    #         settings_cls
    #         # credentials=your_credentials
    #         project_id="lec-sip-dpf-secstore-prod"
    #     )
    #     return (
    #         init_settings,
    #         env_settings,
    #         dotenv_settings,
    #         file_secret_settings,
    #         gcp_settings
    #     )


settings = Settings()
