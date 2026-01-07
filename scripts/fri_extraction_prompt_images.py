"""
FRI Extraction Images Upload Script

This script uploads PNG images from local storage or Google Drive to a GCS bucket
within the path structure: images/fri/extraction/

Usage (Local files):
    python fri_extraction_prompt_images.py --project-id <project-id> \
        --bucket-name <bucket-name> --local-images-path <path-to-images>

Usage (Google Drive folder):
    python fri_extraction_prompt_images.py --project-id <project-id> \
        --bucket-name <bucket-name> --gdrive-folder-id <folder-id>
"""

import argparse
import io
import logging
from pathlib import Path
from typing import List

from google.api_core import exceptions
from google.cloud import storage
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

    def list_png_files(self, folder_id: str) -> List[tuple]:
        """
        List all PNG files in a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            List of tuples (file_id, file_name)
        """
        try:
            query = (
                f"'{folder_id}' in parents and mimeType='image/png' and trashed=false"
            )
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
            logger.info(f"Found {len(files)} PNG file(s) in Google Drive folder")
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


class ImageUploader:
    """Manages PNG image uploads to GCS bucket."""

    # Target path structure in GCS bucket
    TARGET_PATH = "images/fri/extraction/"

    def __init__(self, project_id: str, bucket_name: str):
        """
        Initialize GCS client and bucket.

        Args:
            project_id: GCP Project ID
            bucket_name: Name of the GCS bucket
        """
        self.client = storage.Client(project=project_id)
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.bucket = None

    def ensure_bucket_exists(self) -> storage.Bucket:
        """
        Ensure the bucket exists. If not, raise an error.

        Returns:
            Bucket object

        Raises:
            ValueError: If bucket doesn't exist
        """
        try:
            self.bucket = self.client.get_bucket(self.bucket_name)
            logger.info(f"✓ Found bucket: {self.bucket_name}")
            return self.bucket
        except exceptions.NotFound:
            logger.error(f"Bucket {self.bucket_name} does not exist.")
            logger.error(
                "Please create the bucket first or specify an existing bucket."
            )
            raise ValueError(f"Bucket {self.bucket_name} not found")

    def get_png_files(self, local_path: str) -> List[Path]:
        """
        Get all PNG files from the local directory.

        Args:
            local_path: Path to local directory containing PNG files

        Returns:
            List of Path objects for PNG files

        Raises:
            ValueError: If directory doesn't exist or no PNG files found
        """
        path = Path(local_path)

        if not path.exists():
            logger.error(f"Directory {local_path} does not exist.")
            raise ValueError(f"Directory not found: {local_path}")

        if not path.is_dir():
            logger.error(f"{local_path} is not a directory.")
            raise ValueError(f"Not a directory: {local_path}")

        # Get all PNG files (case-insensitive)
        png_files = [
            f for f in path.iterdir() if f.is_file() and f.suffix.lower() in [".png"]
        ]

        if not png_files:
            logger.error(f"No PNG files found in {local_path}")
            raise ValueError(f"No PNG files found in directory: {local_path}")

        logger.info(f"Found {len(png_files)} PNG file(s) in {local_path}")
        return sorted(png_files)

    def upload_images(self, local_path: str) -> None:
        """
        Upload all PNG images from local directory to GCS bucket.

        Args:
            local_path: Path to local directory containing PNG files
        """
        # Ensure bucket exists
        self.ensure_bucket_exists()

        # Get PNG files
        png_files = self.get_png_files(local_path)

        logger.info(
            f"\nUploading {len(png_files)} PNG file(s) to gs://{self.bucket_name}/{self.TARGET_PATH}"
        )
        logger.info("-" * 80)

        uploaded_count = 0
        failed_count = 0

        for png_file in png_files:
            # Construct the full GCS path
            gcs_path = f"{self.TARGET_PATH}{png_file.name}"
            blob = self.bucket.blob(gcs_path)

            try:
                # Upload file with content type
                blob.upload_from_filename(png_file, content_type="image/png")
                uploaded_count += 1
                logger.info(
                    f"  ✓ Uploaded: {png_file.name} → gs://{self.bucket_name}/{gcs_path}"
                )
            except Exception as e:
                failed_count += 1
                logger.error(f"  ✗ Failed to upload {png_file.name}: {str(e)}")

        logger.info("-" * 80)
        logger.info(f"\nUpload Summary:")
        logger.info(f"  Total files: {len(png_files)}")
        logger.info(f"  Successfully uploaded: {uploaded_count}")
        logger.info(f"  Failed: {failed_count}")

        if failed_count > 0:
            raise Exception(f"{failed_count} file(s) failed to upload")

        logger.info(
            f"\n✓ All images uploaded successfully to gs://{self.bucket_name}/{self.TARGET_PATH}"
        )

    def upload_images_from_gdrive(self, gdrive_folder_id: str) -> None:
        """
        Upload all PNG images from Google Drive folder to GCS bucket.

        Args:
            gdrive_folder_id: Google Drive folder ID
        """
        # Ensure bucket exists
        self.ensure_bucket_exists()

        # Get PNG files from Google Drive
        drive_manager = GoogleDriveManager()
        png_files = drive_manager.list_png_files(gdrive_folder_id)

        if not png_files:
            logger.error(
                f"No PNG files found in Google Drive folder {gdrive_folder_id}"
            )
            raise ValueError(
                f"No PNG files found in Google Drive folder: {gdrive_folder_id}"
            )

        logger.info(
            f"\nUploading {len(png_files)} PNG file(s) from Google Drive to gs://{self.bucket_name}/{self.TARGET_PATH}"
        )
        logger.info("-" * 80)

        uploaded_count = 0
        failed_count = 0

        for file_id, file_name in png_files:
            # Construct the full GCS path
            gcs_path = f"{self.TARGET_PATH}{file_name}"
            blob = self.bucket.blob(gcs_path)

            try:
                # Download from Google Drive and upload to GCS
                file_content = drive_manager.download_file(file_id)
                blob.upload_from_string(file_content, content_type="image/png")
                uploaded_count += 1
                logger.info(
                    f"  ✓ Uploaded: {file_name} → gs://{self.bucket_name}/{gcs_path}"
                )
            except Exception as e:
                failed_count += 1
                logger.error(f"  ✗ Failed to upload {file_name}: {str(e)}")

        logger.info("-" * 80)
        logger.info(f"\nUpload Summary:")
        logger.info(f"  Total files: {len(png_files)}")
        logger.info(f"  Successfully uploaded: {uploaded_count}")
        logger.info(f"  Failed: {failed_count}")

        if failed_count > 0:
            raise Exception(f"{failed_count} file(s) failed to upload")

        logger.info(
            f"\n✓ All images uploaded successfully to gs://{self.bucket_name}/{self.TARGET_PATH}"
        )

    def list_uploaded_images(self) -> List[str]:
        """
        List all images in the target path.

        Returns:
            List of image paths in the bucket
        """
        if not self.bucket:
            self.ensure_bucket_exists()

        blobs = list(self.bucket.list_blobs(prefix=self.TARGET_PATH))
        image_paths = [blob.name for blob in blobs if blob.name.endswith(".png")]

        logger.info(
            f"\nFound {len(image_paths)} PNG image(s) in gs://{self.bucket_name}/{self.TARGET_PATH}"
        )
        for path in image_paths:
            logger.info(f"  - {path}")

        return image_paths


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Upload PNG images to GCS bucket for FRI extraction."
    )
    parser.add_argument("--project-id", required=True, help="GCP Project ID")
    parser.add_argument(
        "--bucket-name", required=True, help="GCS Bucket name (must already exist)"
    )
    parser.add_argument(
        "--local-images-path",
        default=None,
        help="Path to local directory containing PNG images (optional)",
    )
    parser.add_argument(
        "--gdrive-folder-id",
        default=None,
        help="Google Drive folder ID containing PNG images (optional)",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list existing images in the bucket (don't upload)",
    )

    args = parser.parse_args()

    try:
        logger.info("=" * 80)
        logger.info("FRI Extraction Images Upload Script")
        logger.info("=" * 80)
        logger.info(f"Project ID: {args.project_id}")
        logger.info(f"Bucket: {args.bucket_name}")
        logger.info(f"Target path: images/fri/extraction/")

        # Initialize uploader
        uploader = ImageUploader(args.project_id, args.bucket_name)

        if args.list_only:
            # Just list existing images
            logger.info("\n--- Listing Existing Images ---")
            uploader.list_uploaded_images()
        elif args.local_images_path:
            # Upload images from local path
            logger.info(f"Local images path: {args.local_images_path}")
            logger.info("\n--- Starting Upload Process (Local) ---")
            uploader.upload_images(args.local_images_path)
        elif args.gdrive_folder_id:
            # Upload images from Google Drive
            logger.info(f"Google Drive folder ID: {args.gdrive_folder_id}")
            logger.info("\n--- Starting Upload Process (Google Drive) ---")
            uploader.upload_images_from_gdrive(args.gdrive_folder_id)
        else:
            logger.error(
                "Error: Either --local-images-path or --gdrive-folder-id must be provided"
            )
            raise ValueError(
                "Please provide either --local-images-path or --gdrive-folder-id"
            )

        logger.info("\n" + "=" * 80)
        logger.info("✓ Process completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error(f"✗ Process failed: {str(e)}")
        logger.error("=" * 80)
        raise


if __name__ == "__main__":
    main()
