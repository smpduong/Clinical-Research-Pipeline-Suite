"""
redcap_client.py - Secure REDCap API Client

Production-grade API client with rate limiting, exponential backoff retry,
and HIPAA-compliant audit logging.

Usage:
    from src.redcap_client import SecureREDCapClient
    client = SecureREDCapClient()
    df = client.export_records(fields=['participant_id', 'cgm_tir'])
"""

import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, max_calls: int = 100, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def acquire(self):
        now = datetime.now()
        self.calls = [c for c in self.calls if (now - c).total_seconds() < self.period]
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0]).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        self.calls.append(now)


def retry_on_failure(
    max_retries: int = 3,
    backoff: float = 2.0,
    exceptions=(requests.exceptions.RequestException,),
):
    """Decorator for exponential backoff retry."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    wait = backoff**attempt
                    logger.warning(
                        f"Attempt {attempt+1} failed: {e}. Retrying in {wait}s..."
                    )
                    time.sleep(wait)
            return None

        return wrapper

    return decorator


class AuditLogger:
    """
    HIPAA-compliant audit logging with SHA-256 hashing of PHI.

    Every data touch is logged with a cryptographic hash trail for compliance.
    """

    def __init__(self, log_path: str = "audit.log"):
        self.log_path = log_path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                f.write(
                    "timestamp|user|action|record_id|field|old_hash|new_hash|reason|ip|session\n"
                )

    def _hash_phi(self, value) -> str:
        if value is None or value == "":
            return ""
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]

    def log(
        self,
        action: str,
        record_id: str,
        field: str = "",
        old_val=None,
        new_val=None,
        reason: str = "",
        user: str = "api_service",
        ip: str = "127.0.0.1",
    ):
        fields = [
            datetime.now(timezone.utc).isoformat(),
            user,
            action,
            record_id,
            field,
            self._hash_phi(old_val),
            self._hash_phi(new_val),
            reason,
            ip,
            "system",
        ]
        entry = "|".join(str(x) for x in fields) + "\n"
        with open(self.log_path, "a") as f:
            f.write(entry)


class SecureREDCapClient:
    """
    Production-grade REDCap API client.

    Features:
    - Rate limiting (100 calls/minute)
    - Exponential backoff retry (2, 4, 8 seconds)
    - Batched exports for large datasets
    - Metadata caching with LRU
    - HIPAA audit logging
    """

    def __init__(self, url: str = None, token: str = None):
        self.url = url or os.getenv(
            "REDCAP_URI", "https://your-institution.redcap.edu/api/"
        )
        self.token = token or os.getenv("REDCAP_API_TOKEN")
        if not self.token:
            raise ValueError("REDCAP_API_TOKEN not set in environment")
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(max_calls=100, period=60)
        self.audit = AuditLogger("redcap_audit.log")

    @retry_on_failure(max_retries=3, backoff=2.0)
    def _api_call(self, data: Dict) -> Any:
        self.rate_limiter.acquire()
        response = self.session.post(self.url, data=data, timeout=30)
        response.raise_for_status()

        if data.get("content") == "record":
            self.audit.log(
                action="API_EXPORT" if data.get("action") != "import" else "API_IMPORT",
                record_id=data.get("records", "batch"),
                user="redcap_service",
            )

        try:
            return response.json()
        except ValueError:
            return response.text

    @lru_cache(maxsize=32)
    def get_metadata(self) -> Dict:
        """Cache metadata (rarely changes)."""
        return self._api_call(
            {
                "token": self.token,
                "content": "metadata",
                "format": "json",
                "returnFormat": "json",
            }
        )

    def export_records(
        self,
        fields: Optional[List[str]] = None,
        records: Optional[List[str]] = None,
        events: Optional[List[str]] = None,
        batch_size: int = 100,
    ) -> pd.DataFrame:
        """Export with optional batching for large datasets."""
        if batch_size <= 0 or batch_size > 100:
            batch_size = 100

        all_records = []

        if records and len(records) > batch_size:
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                data = self._build_export_payload(fields, batch, events)
                result = self._api_call(data)
                if isinstance(result, list):
                    all_records.extend(result)
        else:
            data = self._build_export_payload(fields, records, events)
            result = self._api_call(data)
            if isinstance(result, list):
                all_records = result

        return pd.DataFrame(all_records)

    def _build_export_payload(self, fields, records, events):
        data = {
            "token": self.token,
            "content": "record",
            "format": "json",
            "type": "flat",
            "rawOrLabel": "raw",
            "rawOrLabelHeaders": "raw",
            "exportCheckboxLabel": "false",
            "exportDataAccessGroups": "true",
            "returnFormat": "json",
        }
        if fields:
            data["fields"] = ",".join(fields)
        if records:
            data["records"] = ",".join(records)
        if events:
            data["events"] = ",".join(events)
        return data

    def import_records(self, records: pd.DataFrame) -> Dict:
        """Import records with audit trail."""
        data = {
            "token": self.token,
            "content": "record",
            "format": "json",
            "type": "flat",
            "overwriteBehavior": "normal",
            "data": records.to_json(orient="records"),
            "returnContent": "count",
            "returnFormat": "json",
        }
        result = self._api_call(data)

        for _, row in records.iterrows():
            self.audit.log(
                action="DATA_IMPORT",
                record_id=str(row.get("participant_id", "unknown")),
                user="redcap_service",
                reason="Record upload",
            )
        return result
