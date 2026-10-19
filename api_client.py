"""Small HTTP API client with retries and JSON helpers."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

RETRY_STATUS = {429, 500, 502, 503, 504}


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status = status
        self.body = body


class ApiClient:
    def __init__(self, base_url: str, token: str | None = None, timeout: float = 10.0,
                 retries: int = 2, backoff: float = 0.2, sleeper=time.sleep):
        self.base_url = base_url.rstrip("/")
        self.token = token if token is not None else os.environ.get("API_TOKEN")
        self.timeout = timeout
        self.retries = max(0, retries)
        self.backoff = backoff
        self._sleeper = sleeper

    def _request(self, method: str, path: str, payload: dict | None = None,
                 headers: dict | None = None):
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request_headers = {"Accept": "application/json",
                           "User-Agent": "api-client-starter/1.0"}
        if payload is not None:
            request_headers["Content-Type"] = "application/json"
        if self.token:
            request_headers["Authorization"] = f"Bearer {self.token}"
        if headers:
            request_headers.update(headers)

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            request = urllib.request.Request(url, data=data, method=method,
                                             headers=request_headers)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return response.status, response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")
                if exc.code in RETRY_STATUS and attempt < self.retries:
                    last_error = ApiError(f"HTTP {exc.code}", exc.code, body)
                else:
                    raise ApiError(f"HTTP {exc.code} for {url}", exc.code, body) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = ApiError(f"request failed: {exc}")
                if attempt >= self.retries:
                    raise last_error from exc
            if attempt < self.retries:
                self._sleeper(self.backoff * (2 ** attempt))
        raise last_error or ApiError("request failed")

    def get_json(self, path: str, headers: dict | None = None) -> Any:
        status, body = self._request("GET", path, headers=headers)
        return json.loads(body) if body else None

    def post_json(self, path: str, payload: dict, headers: dict | None = None) -> Any:
        status, body = self._request("POST", path, payload, headers)
        return json.loads(body) if body else None
