"""Main module for processing entries with extraction and validation."""

import asyncio
import logging

# import google.cloud.logging
from src.config import settings
from src.core import (
    get_entries_to_process_from_bigquery,
    insert_processed_entries_to_bigquery,
    process_entries,
)

# logging_client = google.cloud.logging.Client()
# logging_client.setup_logging()

logs_explorer = logging.getLogger(settings.logger_name)
logs_explorer.setLevel(logging.INFO)


def main():
    """Main function to process entries."""
    entries = get_entries_to_process_from_bigquery(
        settings.bigquery_source_node_name,
        settings.bigquery_source_dataset_name,
        settings.bigquery_source_table_name,
    )
    print("Entries to process:")
    for entry in entries:
        print(entry)
    processed_entries = asyncio.run(process_entries(entries))
    # insert_processed_entries_to_bigquery(
    # processed_entries,
    # settings.bigquery_destination_node_name,
    # settings.bigquery_destination_dataset_name,
    # settings.bigquery_destination_table_name,
    # )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logs_explorer.error(f"An error occurred: {e}")
        logging.shutdown()
