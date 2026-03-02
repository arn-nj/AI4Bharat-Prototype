"""
s3_storage.py — S3 storage utilities for the E-Waste Asset Lifecycle Optimizer
===============================================================================

Provides helpers for:
  - Uploading/downloading ML model artifacts to/from S3
  - Storing analysis results (JSON) in S3
  - Fetching model metadata from S3
  - Uploading compliance documents

Environment variables:
  S3_BUCKET_NAME         — Target S3 bucket (required)
  S3_MODEL_PREFIX        — Key prefix for model artifacts (default: models/)
  S3_RESULTS_PREFIX      — Key prefix for analysis results (default: results/)
  S3_DOCUMENTS_PREFIX    — Key prefix for compliance docs (default: documents/)
  AWS_REGION             — AWS region (default: us-east-1)
"""

from __future__ import annotations

import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Resolve .env relative to this file: src/storage/s3_storage.py -> repo root
_DOTENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_DOTENV_PATH)

log = logging.getLogger(__name__)


class S3Storage:
    """
    Centralised S3 storage client for model artifacts, analysis results,
    and compliance documents.
    """

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        self._bucket = bucket_name or os.getenv("S3_BUCKET_NAME", "")
        self._region = region or os.getenv("AWS_REGION", "us-east-1")
        self._model_prefix = os.getenv("S3_MODEL_PREFIX", "models/")
        self._results_prefix = os.getenv("S3_RESULTS_PREFIX", "results/")
        self._documents_prefix = os.getenv("S3_DOCUMENTS_PREFIX", "documents/")

        if not self._bucket:
            log.warning(
                "S3_BUCKET_NAME not set. S3 operations will fail. "
                "Set it in .env or as an environment variable."
            )

        self._client = boto3.client("s3", region_name=self._region)
        log.info("S3Storage initialised — bucket=%s  region=%s", self._bucket, self._region)

    # ------------------------------------------------------------------
    # Model artifact operations
    # ------------------------------------------------------------------

    def upload_model_artifact(self, local_path: str | Path, key_name: Optional[str] = None) -> str:
        """
        Upload a model artifact (e.g., .joblib file) to S3.

        Parameters
        ----------
        local_path : path to the local file
        key_name   : optional S3 key name (defaults to filename)

        Returns
        -------
        The full S3 key of the uploaded object.
        """
        local_path = Path(local_path)
        key = f"{self._model_prefix}{key_name or local_path.name}"

        log.info("Uploading model artifact: %s → s3://%s/%s", local_path, self._bucket, key)
        self._client.upload_file(str(local_path), self._bucket, key)
        return key

    def download_model_artifact(self, key_name: str, local_path: str | Path) -> Path:
        """
        Download a model artifact from S3 to a local path.

        Parameters
        ----------
        key_name   : S3 key (relative to model prefix, or full key)
        local_path : where to save the file locally

        Returns
        -------
        Path to the downloaded file.
        """
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Support both full key and relative key
        full_key = key_name if key_name.startswith(self._model_prefix) else f"{self._model_prefix}{key_name}"

        log.info("Downloading model artifact: s3://%s/%s → %s", self._bucket, full_key, local_path)
        self._client.download_file(self._bucket, full_key, str(local_path))
        return local_path

    def get_model_metadata(self, key_name: str = "model_metadata.json") -> dict:
        """
        Fetch and parse model_metadata.json from S3.
        """
        full_key = f"{self._model_prefix}{key_name}"
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=full_key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            log.error("Failed to fetch model metadata from S3: %s", e)
            raise

    def model_artifact_exists(self, key_name: str) -> bool:
        """Check whether a model artifact exists in S3."""
        full_key = f"{self._model_prefix}{key_name}"
        try:
            self._client.head_object(Bucket=self._bucket, Key=full_key)
            return True
        except ClientError:
            return False

    # ------------------------------------------------------------------
    # Analysis result operations
    # ------------------------------------------------------------------

    def store_analysis_result(self, asset_id: str, result: dict) -> str:
        """
        Store an analysis result as JSON in S3.

        Key format: results/{asset_id}/{timestamp}.json

        Returns the S3 key of the stored object.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = f"{self._results_prefix}{asset_id}/{timestamp}.json"

        body = json.dumps(result, indent=2, default=str)
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        log.info("Stored analysis result: s3://%s/%s", self._bucket, key)
        return key

    def get_analysis_result(self, s3_key: str) -> dict:
        """Fetch a previously stored analysis result from S3."""
        response = self._client.get_object(Bucket=self._bucket, Key=s3_key)
        return json.loads(response["Body"].read().decode("utf-8"))

    def list_analysis_results(self, asset_id: str, max_results: int = 50) -> list[str]:
        """
        List S3 keys for all stored analysis results for a given asset_id.
        Returns keys sorted by most recent first.
        """
        prefix = f"{self._results_prefix}{asset_id}/"
        response = self._client.list_objects_v2(
            Bucket=self._bucket,
            Prefix=prefix,
            MaxKeys=max_results,
        )
        keys = [obj["Key"] for obj in response.get("Contents", [])]
        return sorted(keys, reverse=True)

    # ------------------------------------------------------------------
    # Compliance document operations
    # ------------------------------------------------------------------

    def upload_compliance_document(
        self,
        asset_id: str,
        document_type: str,
        file_content: bytes,
        file_extension: str = ".pdf",
    ) -> str:
        """
        Upload a compliance document to S3.

        Key format: documents/{asset_id}/{document_type}_{timestamp}{ext}

        Returns the S3 key.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = f"{self._documents_prefix}{asset_id}/{document_type}_{timestamp}{file_extension}"

        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=file_content,
        )
        log.info("Uploaded compliance document: s3://%s/%s", self._bucket, key)
        return key

    def get_compliance_document(self, s3_key: str) -> bytes:
        """Download a compliance document from S3."""
        response = self._client.get_object(Bucket=self._bucket, Key=s3_key)
        return response["Body"].read()

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def upload_json(self, key: str, data: Any) -> str:
        """Upload a JSON-serialisable object to S3."""
        body = json.dumps(data, indent=2, default=str)
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        return key

    def download_json(self, key: str) -> Any:
        """Download and parse a JSON object from S3."""
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))

    def file_exists(self, key: str) -> bool:
        """Check if an object exists in the configured bucket."""
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for downloading an S3 object."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
