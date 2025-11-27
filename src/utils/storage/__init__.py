"""Cloud storage upload utilities.

Supports multiple providers:
- AWS S3
- Cloudflare R2 (zero egress fees)
- Alibaba Cloud OSS
- Disabled mode (none)

Configuration via config.yaml or STORAGE_PROVIDER env var.
"""

from src.utils.storage.storage_uploader import (
    is_storage_enabled,
    upload_file,
    upload_bytes,
    upload_base64,
    get_public_url,
    get_signed_url,
    does_object_exist,
    delete_object,
    upload_image,
    upload_chart,
    verify_connection,
    get_provider_name,
    get_provider_id,
)

__all__ = [
    "is_storage_enabled",
    "upload_file",
    "upload_bytes",
    "upload_base64",
    "get_public_url",
    "get_signed_url",
    "does_object_exist",
    "delete_object",
    "upload_image",
    "upload_chart",
    "verify_connection",
    "get_provider_name",
    "get_provider_id",
]
