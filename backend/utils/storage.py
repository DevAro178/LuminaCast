import os
import boto3
import logging
from pathlib import Path
from config import (
    S3_ENABLED, S3_ACCESS_KEY, S3_SECRET_KEY, 
    S3_BUCKET_NAME, S3_REGION, S3_CUSTOM_DOMAIN
)

logger = logging.getLogger(__name__)

class S3Storage:
    def __init__(self):
        self.enabled = S3_ENABLED
        self.s3 = None
        if self.enabled:
            try:
                self.s3 = boto3.client(
                    's3',
                    aws_access_key_id=S3_ACCESS_KEY,
                    aws_secret_access_key=S3_SECRET_KEY,
                    region_name=S3_REGION
                )
                self.bucket = S3_BUCKET_NAME
                self.custom_domain = S3_CUSTOM_DOMAIN
                logger.info(f"S3 Storage initialized (bucket: {self.bucket})")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self.enabled = False

    def upload_file(self, local_path: str | Path, s3_key: str) -> str:
        """
        Upload a file to S3 and return the URL.
        If S3 is disabled or upload fails, returns the local path string.
        """
        local_path = Path(local_path)
        if not self.enabled or not self.s3:
            return str(local_path)

        if not local_path.exists():
            logger.error(f"Local file not found for upload: {local_path}")
            return str(local_path)

        try:
            # Determine ContentType
            content_type = "application/octet-stream"
            suffix = local_path.suffix.lower()
            if suffix in [".jpg", ".jpeg"]:
                content_type = "image/jpeg"
            elif suffix == ".png":
                content_type = "image/png"
            elif suffix == ".mp3":
                content_type = "audio/mpeg"
            elif suffix == ".mp4":
                content_type = "video/mp4"
            elif suffix == ".ass":
                content_type = "text/plain"

            self.s3.upload_file(
                str(local_path),
                self.bucket,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            if self.custom_domain:
                url = f"https://{self.custom_domain}/{s3_key}"
            else:
                url = f"https://{self.bucket}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
            
            logger.info(f"Uploaded {local_path.name} to S3: {url}")
            return url
                
        except Exception as e:
            logger.error(f"Failed to upload {local_path} to S3: {e}")
            return str(local_path)

# Singleton instance
storage = S3Storage()
