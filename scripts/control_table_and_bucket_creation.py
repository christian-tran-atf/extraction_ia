"""
BigQuery Table and GCS Bucket Creation Script

This script automates the creation of:
1. BigQuery table for extraction control with proper schema, partitioning, and clustering
2. GCS bucket for storing PDF files
3. Upload of local or Google Drive PDF files to the GCS bucket

Usage (Local files):
    python control_table_and_bucket_creation.py --project-id <project-id> --dataset-id <dataset-id> \
        --table-id <table-id> --bucket-name <bucket-name> --local-pdfs-path <path-to-pdfs>

Usage (Google Drive folder):
    python control_table_and_bucket_creation.py --project-id <project-id> --dataset-id <dataset-id> \
        --table-id <table-id> --bucket-name <bucket-name> --gdrive-folder-id <folder-id>
"""

import argparse
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from google.api_core import exceptions
from google.cloud import bigquery, storage
from google.cloud.bigquery import SchemaField
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class GoogleDriveManager:
    """Manages Google Drive file operations."""

    def __init__(self):
        """Initialize Google Drive client."""
        self.service = build("drive", "v3")

    def list_pdf_files(self, folder_id: str) -> List[tuple]:
        """
        List all PDF files in a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            List of tuples (file_id, file_name)
        """
        try:
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            results = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="files(id, name)",
                    pageSize=1000,
                )
                .execute()
            )
            files = results.get("files", [])
            logger.info(f"Found {len(files)} PDF files in Google Drive folder")
            return [(file["id"], file["name"]) for file in files]
        except HttpError as error:
            logger.error(f"Error accessing Google Drive: {error}")
            raise

    def download_file(self, file_id: str) -> bytes:
        """
        Download a file from Google Drive as bytes.

        Args:
            file_id: Google Drive file ID

        Returns:
            File content as bytes
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            return file_content.getvalue()
        except HttpError as error:
            logger.error(f"Error downloading file from Google Drive: {error}")
            raise


class BigQueryTableManager:
    """Manages BigQuery table creation and data insertion."""

    def __init__(self, project_id: str):
        """Initialize BigQuery client."""
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id

    def create_table(
        self, dataset_id: str, table_id: str, location: str = "US"
    ) -> bigquery.Table:
        """
        Create a BigQuery table with proper schema, partitioning, and clustering.

        Args:
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
            location: BigQuery location (default: US)

        Returns:
            Created table object
        """
        table_id_full = f"{self.project_id}.{dataset_id}.{table_id}"

        # Define schema
        schema = [
            SchemaField("id", "STRING", mode="REQUIRED"),
            SchemaField("id_source", "STRING", mode="NULLABLE"),
            SchemaField("type_de_document", "STRING", mode="NULLABLE"),
            SchemaField("lien_gcs", "STRING", mode="NULLABLE"),
            SchemaField(
                "statut_extraction",
                "STRING",
                mode="NULLABLE",
                default_value_expression="'PENDING'",
            ),
            SchemaField(
                "tentatives", "INTEGER", mode="NULLABLE", default_value_expression="0"
            ),
            SchemaField(
                "date_creation",
                "DATETIME",
                mode="NULLABLE",
                default_value_expression="CURRENT_DATETIME()",
            ),
            SchemaField("date_derniere_modification", "DATETIME", mode="NULLABLE"),
            SchemaField("tech_interface_id", "STRING", mode="NULLABLE"),
            SchemaField("tech_timestamp", "TIMESTAMP", mode="NULLABLE"),
        ]

        # Create table object with schema
        table = bigquery.Table(table_id_full, schema=schema)

        # Set partitioning
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="date_creation",
        )

        # Set clustering
        table.clustering_fields = ["statut_extraction", "type_de_document"]

        try:
            # Check if table already exists
            self.client.get_table(table_id_full)
            logger.info(f"Table {table_id_full} already exists. Skipping creation.")
            return self.client.get_table(table_id_full)
        except exceptions.NotFound:
            logger.info(f"Creating table {table_id_full}...")
            table = self.client.create_table(table)
            logger.info(f"✓ Table {table_id_full} created successfully")
            return table

    def insert_sample_data(
        self, dataset_id: str, table_id: str, rows: List[Dict[str, Any]]
    ) -> None:
        """
        Insert sample data into the table.

        Args:
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
            rows: List of dictionaries containing row data
        """
        table_id_full = f"{self.project_id}.{dataset_id}.{table_id}"

        try:
            errors = self.client.insert_rows_json(table_id_full, rows)
            if errors:
                logger.error(f"Errors inserting rows into {table_id_full}: {errors}")
                raise Exception(f"Failed to insert rows: {errors}")
            logger.info(
                f"✓ Successfully inserted {len(rows)} rows into {table_id_full}"
            )
        except Exception as e:
            logger.error(f"Error inserting data: {str(e)}")
            raise


class GCSBucketManager:
    """Manages GCS bucket creation and file uploads."""

    def __init__(self, project_id: str):
        """Initialize GCS client."""
        self.client = storage.Client(project=project_id)
        self.project_id = project_id

    def create_bucket(self, bucket_name: str, location: str = "US") -> storage.Bucket:
        """
        Create a GCS bucket.

        Args:
            bucket_name: Name of the bucket to create
            location: Bucket location (default: US)

        Returns:
            Created bucket object
        """
        try:
            bucket = self.client.get_bucket(bucket_name)
            logger.info(f"Bucket {bucket_name} already exists. Skipping creation.")
            return bucket
        except exceptions.NotFound:
            logger.info(f"Creating bucket {bucket_name}...")
            bucket = self.client.create_bucket(bucket_name, location=location)
            logger.info(f"✓ Bucket {bucket_name} created successfully")
            return bucket

    def create_pdfs_folder(self, bucket_name: str) -> None:
        """
        Create a 'pdfs' folder in the bucket by uploading a placeholder object.

        Args:
            bucket_name: Name of the bucket
        """
        bucket = self.client.get_bucket(bucket_name)
        folder_placeholder = bucket.blob("pdfs/.keep")

        try:
            folder_placeholder.upload_from_string("")
            logger.info(f"✓ Created 'pdfs' folder in bucket {bucket_name}")
        except Exception as e:
            logger.error(f"Error creating pdfs folder: {str(e)}")
            raise

    def upload_files(self, bucket_name: str, local_pdfs_path: str) -> None:
        """
        Upload PDF files from local storage to the GCS bucket.

        Args:
            bucket_name: Name of the bucket
            local_pdfs_path: Local directory containing PDF files
        """
        bucket = self.client.get_bucket(bucket_name)
        pdfs_path = Path(local_pdfs_path)

        if not pdfs_path.exists():
            logger.warning(
                f"Local PDF path {local_pdfs_path} does not exist. Skipping file upload."
            )
            return

        pdf_files = list(pdfs_path.glob("*.pdf"))

        if not pdf_files:
            logger.warning(
                f"No PDF files found in {local_pdfs_path}. Skipping file upload."
            )
            return

        logger.info(
            f"Uploading {len(pdf_files)} PDF files to gs://{bucket_name}/pdfs/..."
        )

        for pdf_file in pdf_files:
            blob = bucket.blob(f"pdfs/{pdf_file.name}")
            try:
                blob.upload_from_filename(pdf_file)
                logger.info(f"  ✓ Uploaded {pdf_file.name}")
            except Exception as e:
                logger.error(f"  ✗ Failed to upload {pdf_file.name}: {str(e)}")
                raise

        logger.info(
            f"✓ Successfully uploaded all PDF files to gs://{bucket_name}/pdfs/"
        )

    def upload_files_from_gdrive(self, bucket_name: str, gdrive_folder_id: str) -> None:
        """
        Upload PDF files from Google Drive folder to the GCS bucket.

        Args:
            bucket_name: Name of the bucket
            gdrive_folder_id: Google Drive folder ID
        """
        bucket = self.client.get_bucket(bucket_name)
        drive_manager = GoogleDriveManager()
        pdf_files = drive_manager.list_pdf_files(gdrive_folder_id)

        if not pdf_files:
            logger.warning(
                f"No PDF files found in Google Drive folder {gdrive_folder_id}. Skipping file upload."
            )
            return

        logger.info(
            f"Uploading {len(pdf_files)} PDF files from Google Drive to gs://{bucket_name}/pdfs/..."
        )

        for file_id, file_name in pdf_files:
            blob = bucket.blob(f"pdfs/{file_name}")
            try:
                file_content = drive_manager.download_file(file_id)
                blob.upload_from_string(file_content, content_type="application/pdf")
                logger.info(f"  ✓ Uploaded {file_name}")
            except Exception as e:
                logger.error(f"  ✗ Failed to upload {file_name}: {str(e)}")
                raise

        logger.info(
            f"✓ Successfully uploaded all PDF files to gs://{bucket_name}/pdfs/"
        )


def get_sample_data() -> List[Dict[str, Any]]:
    """
    Get sample data for insertion into the BigQuery table.

    Returns:
        List of dictionaries containing sample row data
    """
    return [
        {
            "id": "0",
            "type_de_document": "FRI",
            "lien_gcs": "gs://BUCKET_NAME/pdfs/404JG01613 PO1042511 INSP_40-2025-05-004087-Z006_LEC10.pdf",
        },
        {
            "id": "1",
            "type_de_document": "FRI",
            "lien_gcs": "gs://BUCKET_NAME/pdfs/412CUI00751 PO1042967 INSP HGHWT00363275 LEC511572.pdf",
        },
        {
            "id": "2",
            "type_de_document": "FRI",
            "lien_gcs": "gs://BUCKET_NAME/pdfs/412CUI00751 PO1042967 Re-INSP HGHWT00364666 LEC511572.pdf",
        },
        {
            "id": "3",
            "type_de_document": "FRI",
            "lien_gcs": "gs://BUCKET_NAME/pdfs/AT3153B(401ECL00005) PO1041820 INSP 6225018B.00-2 LEC146369.pdf",
        },
        {
            "id": "4",
            "type_de_document": "FRI",
            "lien_gcs": "gs://BUCKET_NAME/pdfs/PUEGPSIA00021 PO1043055 INSP HGHWT00364379 LEC509023.pdf",
        },
        {
            "id": "5",
            "type_de_document": "FRI",
            "lien_gcs": "gs://BUCKET_NAME/pdfs/SOCKBABCOL00037 PO#1043652 insp DSS_CNIR2509SH12911 LEC#012401, 012502.pdf",
        },
        {
            "id": "6",
            "type_de_document": "FRI",
            "lien_gcs": "gs://BUCKET_NAME/pdfs/UWWOSG00558 PO 1043119 insp DSS_CNIR2509SZ07627 LEC 451578,451547,451349,451493,451523,451455,451486 ...ETC..pdf",
        },
        {
            "id": "7",
            "type_de_document": "FRI",
            "lien_gcs": "gs://BUCKET_NAME/pdfs/WG113W WG116W WG126 PO1043979 SAMPLING WHGHWT00364233 LEC5470 5472 5477.pdf",
        },
    ]


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Create BigQuery table and GCS bucket for extraction control."
    )
    parser.add_argument("--project-id", required=True, help="GCP Project ID")
    parser.add_argument(
        "--dataset-id",
        required=True,
        help="BigQuery Dataset ID",
    )
    parser.add_argument(
        "--table-id",
        default="controle_extraction_ia",
        help="BigQuery Table ID (default: controle_extraction_ia)",
    )
    parser.add_argument(
        "--bucket-name",
        required=True,
        help="GCS Bucket name",
    )
    parser.add_argument(
        "--local-pdfs-path",
        default=None,
        help="Path to local PDFs directory (optional)",
    )
    parser.add_argument(
        "--gdrive-folder-id",
        default=None,
        help="Google Drive folder ID containing PDFs (optional)",
    )
    parser.add_argument(
        "--location",
        default="US",
        help="GCP location for bucket and dataset (default: US)",
    )

    args = parser.parse_args()

    try:
        logger.info("Starting BigQuery table and GCS bucket creation process...")
        logger.info(f"Project ID: {args.project_id}")
        logger.info(f"Dataset ID: {args.dataset_id}")
        logger.info(f"Table ID: {args.table_id}")
        logger.info(f"Bucket Name: {args.bucket_name}")

        # Create BigQuery table
        logger.info("\n--- Creating BigQuery Table ---")
        bq_manager = BigQueryTableManager(args.project_id)
        bq_manager.create_table(args.dataset_id, args.table_id, location=args.location)

        # Insert sample data
        logger.info("\n--- Inserting Sample Data ---")
        sample_data = get_sample_data()
        # Replace BUCKET_NAME placeholder with actual bucket name
        for row in sample_data:
            row["lien_gcs"] = row["lien_gcs"].replace("BUCKET_NAME", args.bucket_name)
        bq_manager.insert_sample_data(args.dataset_id, args.table_id, sample_data)

        # Create GCS bucket
        logger.info("\n--- Creating GCS Bucket ---")
        gcs_manager = GCSBucketManager(args.project_id)
        gcs_manager.create_bucket(args.bucket_name, location=args.location)

        # Create pdfs folder
        logger.info("\n--- Creating PDFs Folder ---")
        gcs_manager.create_pdfs_folder(args.bucket_name)

        # Upload files if local path provided
        if args.local_pdfs_path:
            logger.info("\n--- Uploading PDF Files (Local) ---")
            gcs_manager.upload_files(args.bucket_name, args.local_pdfs_path)
        elif args.gdrive_folder_id:
            logger.info("\n--- Uploading PDF Files (Google Drive) ---")
            gcs_manager.upload_files_from_gdrive(
                args.bucket_name, args.gdrive_folder_id
            )
        else:
            logger.info("\n--- Skipping file upload (no source specified) ---")

        logger.info("\n✓ Process completed successfully!")
        logger.info(
            f"\nBigQuery Table: {args.project_id}.{args.dataset_id}.{args.table_id}"
        )
        logger.info(f"GCS Bucket: gs://{args.bucket_name}/pdfs/")

    except Exception as e:
        logger.error(f"\n✗ Process failed with error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
