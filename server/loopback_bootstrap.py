"""Read-only localhost-only transport for synthetic Tasks bootstrap page tests.

Never accepts remote origins, proxy settings, redirects, bearer tokens on a
command line, or a non-loopback host. This is an experimental one-user
development adapter, not an authenticated remote-device or production client.
"""
from __future__ import annotations

from http.client import HTTPConnection, HTTPException
import json
import math
from urllib.parse import urlencode

from bootstrap_client import SnapshotChanged
from outbox import OutboxError, canonical_uuid

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_CONTENT_TYPE = "application/json; charset=utf-8"


def _unique_json_object(pairs):
    value = {}
    for key, field in pairs:
        if key in value:
            raise ValueError("Ambiguous duplicate JSON property")
        value[key] = field
    return value


def _reject_nonfinite(_value):
    raise ValueError("Nonstandard JSON constant")


class LoopbackBootstrapTransport:
    """A fixed 127.0.0.1 read-only GET connector with short-lived token use."""

    __slots__ = ("_port", "_token", "_timeout")

    def __init__(self, port: int, token: str, *, timeout: float = 3.0):
        if type(port) is not int or not 1 <= port <= 65535:
            raise OutboxError("Invalid local Tasks port")
        if (not isinstance(token, str) or not 32 <= len(token) <= 512
                or any(not 33 <= ord(ch) <= 126 for ch in token)):
            raise OutboxError("Invalid local Tasks bearer credential")
        if (type(timeout) not in (int, float) or not math.isfinite(timeout)
                or not 0.1 <= timeout <= 10):
            raise OutboxError("Invalid local transport timeout")
        self._port = port
        self._token = token
        self._timeout = timeout

    def __repr__(self):
        # Do not reveal credentials in default debugging/exception messages.
        return "<LoopbackBootstrapTransport 127.0.0.1, token=[redacted]>"

    def fetch_page(self, *, limit: int, after: str | None, checkpoint: int | None) -> dict:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise OutboxError("Invalid Tasks page limit")
        query = {"limit": str(limit)}
        if after is not None:
            query["after"] = canonical_uuid(after)
            if type(checkpoint) is not int or not 0 <= checkpoint < 2**63:
                raise OutboxError("Invalid Tasks continuation checkpoint")
            query["checkpoint"] = str(checkpoint)
        elif checkpoint is not None:
            raise OutboxError("Checkpoint without page cursor")

        path = "/v1/bootstrap-page?" + urlencode(query)
        conn = HTTPConnection("127.0.0.1", self._port, timeout=self._timeout)
        try:
            conn.request("GET", path, headers={
                "Authorization": "Bearer " + self._token,
                "Accept": "application/json",
                "Cache-Control": "no-store",
            })
            response = conn.getresponse()
            if response.status == 409:
                raise SnapshotChanged()
            if response.status != 200:
                # Includes 3xx: http.client does not follow Location at all.
                raise OutboxError("Local bootstrap source denied or unavailable")

            headers = response.getheaders()
            def values(name):
                return [value for key, value in headers if key.lower() == name]
            content_type = values("content-type")
            length_values = values("content-length")
            cache_control = values("cache-control")
            if (len(content_type) != 1 or content_type[0].lower() != _CONTENT_TYPE
                    or len(length_values) != 1 or len(cache_control) != 1
                    or cache_control[0].lower() != "no-store"
                    or values("transfer-encoding") or values("content-encoding")):
                raise OutboxError("Local bootstrap response headers are invalid")
            length = length_values[0]
            if (not length.isascii() or not length.isdecimal() or len(length) > 7
                    or not 0 < int(length) <= MAX_RESPONSE_BYTES):
                raise OutboxError("Local bootstrap response size is invalid")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) != int(length):
                raise OutboxError("Incomplete or oversized bootstrap response")
            try:
                page = json.loads(raw.decode("utf-8"),
                                  object_pairs_hook=_unique_json_object,
                                  parse_constant=_reject_nonfinite)
            except (UnicodeError, ValueError, RecursionError) as exc:
                raise OutboxError("Invalid local bootstrap JSON") from None
            if not isinstance(page, dict):
                raise OutboxError("Invalid local bootstrap JSON object")
            return page
        except (SnapshotChanged, OutboxError):
            raise
        except (OSError, HTTPException, TimeoutError, UnicodeError, ValueError) as exc:
            raise OutboxError("Local bootstrap transport failed") from None
        finally:
            conn.close()
