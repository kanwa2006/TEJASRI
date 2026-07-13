"""AWS S3 integration: audit-log archival and dataset/backup storage.

boto3 is an optional extra (`pip install -e ".[aws]"`) so the core platform
stays runnable at $0 with zero cloud dependencies. Credentials come from the
standard AWS environment/credential chain — never from application config.
"""

import asyncio
import json
from typing import Any

from tejasri.core.errors import ExternalServiceError
from tejasri.core.logging import get_logger

log = get_logger(__name__)


class S3Archiver:
    def __init__(self, bucket: str, region: str) -> None:
        if not bucket:
            raise ExternalServiceError("S3_BUCKET is not configured")
        try:
            import boto3
        except ImportError as exc:
            raise ExternalServiceError(
                'boto3 not installed; install with: pip install -e ".[aws]"'
            ) from exc
        self._bucket = bucket
        self._client = boto3.client("s3", region_name=region)

    async def upload_json(self, key: str, payload: Any) -> str:
        """Upload a JSON document; returns the s3:// URI."""
        body = json.dumps(payload, default=str).encode()

        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
            )

        try:
            await asyncio.to_thread(_put)
        except Exception as exc:
            raise ExternalServiceError(f"s3 upload failed: {exc}") from exc
        uri = f"s3://{self._bucket}/{key}"
        log.info("s3_uploaded", uri=uri, bytes=len(body))
        return uri
