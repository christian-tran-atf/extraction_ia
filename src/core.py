import asyncio
import logging
from typing import Any

from google import genai
from google.cloud import bigquery
from google.genai import types
from pydantic import ValidationError

from src.config import ExtractionDocument, ValidationDocument, settings
from src.models.common import (
    DestinationEntry,
    ExtractionOutput,
    ProcessingOutput,
    SourceEntry,
    ValidationOutput,
)

logs_explorer = logging.getLogger(settings.logger_name)
logs_explorer.setLevel(logging.INFO)

bigquery_client = bigquery.Client()
extraction_semaphore = asyncio.Semaphore(settings.extraction_semaphore_limit)
validation_semaphore = asyncio.Semaphore(settings.validation_semaphore_limit)


def get_entries_to_process_from_bigquery(
    source_node_name: str, source_dataset_name: str, source_table_name: str
) -> list[SourceEntry]:
    """Fetch entries from a BigQuery table based on extraction status.

    Args:
        source_node_name (str): The name of the BigQuery node.
        source_dataset_name (str): The name of the BigQuery dataset.
        source_table_name (str): The name of the BigQuery table.

    Returns:
        list[SourceEntry]: A list of SourceEntry objects to be processed.
    """
    logs_explorer.info(f"Fetching entries from BigQuery table: {source_table_name}...")
    query = _get_bigquery_query_to_fetch_entries(
        source_node_name, source_dataset_name, source_table_name
    )
    try:
        rows = bigquery_client.query_and_wait(query)
    except Exception as e:
        logs_explorer.error(f"Error fetching entries from BigQuery: {e}")
        raise e
    # logs_explorer.info("The query data:")
    # for row in rows:
    # print(
    # f"Row ids: {row.id}, statut_extraction: {row.statut_extraction}, tentatives: {row.tentatives}, lien_gcs: {row.lien_gcs}"
    # )
    source_entries = [SourceEntry(**dict(row)) for row in rows]
    return source_entries


def _get_bigquery_query_to_fetch_entries(
    source_node_name: str, source_dataset_name: str, source_table_name: str
) -> str:
    """Construct the BigQuery SQL query to fetch entries based on extraction status."""
    query = f"""
    SELECT *
    FROM `{source_node_name}.{source_dataset_name}.{source_table_name}`
    WHERE
        statut_extraction = '{settings.pending_status}'
        OR (statut_extraction = '{settings.error_status}' AND tentatives < {settings.attempts_limit})
    """
    return query


async def process_entries(entries: list[SourceEntry]) -> list[DestinationEntry]:
    """Process a list of SourceEntry objects asynchronously

    Args:
        entries (list[SourceEntry]): List of entries to process.

    Returns:
        list[DestinationEntry]: List of processed DestinationEntry objects.
    """
    logs_explorer.info(f"Processing {len(entries)} entries...")
    async with genai.Client(
        http_options=types.HttpOptions(api_version="v1")
    ).aio as genai_async_client:
        active_tasks = set()
        for entry in entries:
            task = asyncio.create_task(process_entry(genai_async_client, entry))
            active_tasks.add(task)
            task.add_done_callback(active_tasks.discard)
        processed_entries = await asyncio.gather(*active_tasks, return_exceptions=True)
    final_entries = []
    for i, result in enumerate(processed_entries):
        if isinstance(result, Exception):
            logs_explorer.error(
                f"Error processing entry with id {entries[i].id}: {result}"
            )
        else:
            final_entries.append(result)
    return final_entries


async def process_entry(
    genai_async_client: Any, entry: SourceEntry
) -> DestinationEntry:
    """Process a single SourceEntry object

    Args:
        genai_async_client (Any): The asynchronous GenAI client.
        entry (SourceEntry): The entry to process.

    Returns:
        DestinationEntry: The processed DestinationEntry object.
    """
    logs_explorer.info(f"Processing entry with id: {entry.id}...")
    entry_document_config = settings.document_config.get(entry.type_de_document)
    if not entry_document_config:
        raise ValueError(
            f"No document configuration found for type_de_document: {entry.type_de_document}"
        )

    if isinstance(entry_document_config, ValidationDocument):
        (
            extraction_output,
            validation_output,
        ) = await _extract_and_validate_content_from_entry(
            genai_async_client, entry, entry_document_config
        )
        logs_explorer.info(
            f"Extraction output for entry id {entry.id}: {extraction_output}"
        )
        logs_explorer.info(
            f"Validation output for entry id {entry.id}: {validation_output}"
        )
        processing_output = ProcessingOutput(
            extraction_output=extraction_output.model_dump(),
            validation_output=validation_output.model_dump(),
        )
        payload_json = processing_output.model_dump_json()
    else:
        extraction_output = await _extract_content_from_entry(
            genai_async_client, entry, entry_document_config
        )
        logs_explorer.info(
            f"Extraction output for entry id {entry.id}: {extraction_output}"
        )
        processing_output = ProcessingOutput(
            extraction_output=extraction_output.model_dump()
        )
        payload_json = processing_output.model_dump_json()

    return DestinationEntry(
        id=entry.id,
        type_de_document=entry.type_de_document,
        payload_json=payload_json,
    )


async def _extract_and_validate_content_from_entry(
    genai_async_client: Any,
    entry: SourceEntry,
    entry_document_config: ValidationDocument,
) -> tuple[ExtractionOutput, ValidationOutput]:
    """Extract and validate content from a SourceEntry object.

    Args:
        genai_async_client (Any): The asynchronous GenAI client.
        entry (SourceEntry): The source entry.
        entry_document_config (ValidationDocument): The document configuration.

    Returns:
        tuple[ExtractionOutput, ValidationOutput]: Extraction and validation outputs.
    """
    try:
        async_chat = genai_async_client.chats.create(
            model=settings.llm_model_id,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        pdf_file = types.Part.from_uri(
            file_uri=entry.lien_gcs,
            mime_type="application/pdf",
        )
        extraction_prompt = types.Part.from_text(
            text=entry_document_config.extraction_prompt
        )
        async with extraction_semaphore:
            extraction_response = await async_chat.send_message(
                message=[
                    pdf_file,
                    extraction_prompt,
                ],
                config=types.GenerateContentConfig(
                    response_json_schema=entry_document_config.extraction_output_schema_model.model_json_schema(),
                ),
            )
        if extraction_response.text is None:
            raise ValueError("No extraction response text")
        extraction_output = (
            entry_document_config.extraction_output_schema_model.model_validate_json(
                extraction_response.text
            )
        )

        validation_prompt = types.Part.from_text(
            text=entry_document_config.validation_prompt.format(
                extraction_output_json=extraction_response.text
            )
        )
        async with validation_semaphore:
            validation_response = await async_chat.send_message(
                message=validation_prompt,
                config=types.GenerateContentConfig(
                    response_json_schema=entry_document_config.validation_output_schema_model.model_json_schema(),
                ),
            )
        if validation_response.text is None:
            raise ValueError("No validation response text")
        validation_output = (
            entry_document_config.validation_output_schema_model.model_validate_json(
                validation_response.text
            )
        )
        return extraction_output, validation_output
    except ValidationError as ve:
        logs_explorer.error(f"Pydantic validation error: {ve}")
        raise ve
    except Exception as e:
        logs_explorer.error(f"Error processing: {e}")
        raise e


async def _extract_content_from_entry(
    genai_async_client: Any,
    entry: SourceEntry,
    entry_document_config: ExtractionDocument,
) -> ExtractionOutput:
    """Extract content from a SourceEntry object using generate_content.

    Args:
        genai_async_client (Any): The asynchronous GenAI client.
        entry (SourceEntry): The entry to extract content from.
        entry_document_config (ExtractionDocument): The document configuration for extraction.

    Returns:
        ExtractionOutput: The extracted content as an ExtractionOutput object.
    """
    try:
        pdf_file = types.Part.from_uri(
            file_uri=entry.lien_gcs,
            mime_type="application/pdf",
        )
        async with extraction_semaphore:
            extraction_response = await genai_async_client.models.generate_content(
                model=settings.llm_model_id,
                contents=types.Content(
                    role="user",
                    parts=[
                        pdf_file,
                        types.Part.from_text(
                            text=entry_document_config.extraction_prompt
                        ),
                    ],
                ),
                config=types.GenerateContentConfig(
                    response_json_schema=entry_document_config.extraction_output_schema_model.model_json_schema(),
                ),
            )
        if extraction_response.text is None:
            raise ValueError("No extraction response text")
        extraction_output = (
            entry_document_config.extraction_output_schema_model.model_validate_json(
                extraction_response.text
            )
        )
        return extraction_output
    except ValidationError as ve:
        logs_explorer.error(f"Pydantic validation error: {ve}")
        raise ve
    except Exception as e:
        logs_explorer.error(f"Extraction error: {e}")
        raise e


def insert_processed_entries_to_bigquery(
    processed_entries: list[DestinationEntry],
    destination_node_name: str,
    destination_dataset_name: str,
    destination_table_name: str,
) -> None:
    """Insert processed entries into a BigQuery table.

    Args:
        processed_entries (list[DestinationEntry]): List of processed entries.
        destination_node_name (str): The name of the BigQuery node.
        destination_dataset_name (str): The name of the BigQuery dataset.
        destination_table_name (str): The name of the BigQuery table.
    """
    logs_explorer.info(
        f"Inserting processed entries into BigQuery table: {destination_table_name}..."
    )
