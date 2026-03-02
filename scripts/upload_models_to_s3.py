#!/usr/bin/env python3
"""
upload_models_to_s3.py — Upload ML model artifacts to S3
=========================================================

Usage:
    python scripts/upload_models_to_s3.py --bucket <bucket-name> [--prefix models/]

Uploads:
    - risk_label_model.joblib
    - model_metadata.json
"""

import argparse
import sys
from pathlib import Path

import boto3


def main():
    parser = argparse.ArgumentParser(description="Upload model artifacts to S3")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--prefix", default="models/", help="S3 key prefix (default: models/)")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()

    model_dir = Path(__file__).parent.parent / "src" / "model_training" / "models"

    if not model_dir.exists():
        print(f"ERROR: Model directory not found: {model_dir}")
        sys.exit(1)

    files_to_upload = [
        "risk_label_model.joblib",
        "model_metadata.json",
    ]

    s3 = boto3.client("s3", region_name=args.region)

    for filename in files_to_upload:
        local_path = model_dir / filename
        if not local_path.exists():
            print(f"  SKIP: {filename} not found at {local_path}")
            continue

        s3_key = f"{args.prefix}{filename}"
        print(f"  Uploading {local_path} → s3://{args.bucket}/{s3_key}")
        s3.upload_file(str(local_path), args.bucket, s3_key)
        print(f"  ✓ Uploaded {filename}")

    print("\nDone.")


if __name__ == "__main__":
    main()
