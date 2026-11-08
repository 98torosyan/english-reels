"""Check the Instagram account and one unpublished media container."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v27.0")
GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"
TEST_IMAGE_URL = (
    "https://raw.githubusercontent.com/98torosyan/english-reading/main/icon-512.png"
)


class GraphError(RuntimeError):
    pass


def request_json(method: str, path: str, values: dict[str, str] | None = None) -> dict:
    token = os.environ["IG_TOKEN"]
    url = f"{GRAPH_BASE}/{path.lstrip('/')}"
    body = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if values is not None:
        encoded = urllib.parse.urlencode(values)
        if method == "GET":
            url = f"{url}?{encoded}"
        else:
            body = encoded.encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8")).get("error", {})
        except (ValueError, AttributeError):
            detail = {}
        code = detail.get("code", "unknown")
        message = detail.get("message", "Graph API request failed")
        raise GraphError(f"Graph API returned HTTP {error.code}, code {code}: {message}") from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise GraphError(f"Network request failed: {error.reason if hasattr(error, 'reason') else error}") from None
    if not isinstance(payload, dict):
        raise GraphError("Graph API returned an unexpected response.")
    return payload


def main() -> int:
    user_id = os.environ.get("IG_USER_ID", "").strip()
    expected = "english.readingroom"
    if not user_id or not os.environ.get("IG_TOKEN"):
        print("IG_TOKEN and IG_USER_ID repository secrets are required.", file=sys.stderr)
        return 2

    try:
        account = request_json("GET", user_id, {"fields": "id,username"})
        username = str(account.get("username", "")).lower()
        if username != expected:
            print(f"Account check failed: expected @{expected}, received @{username or 'unknown'}.")
            return 1
        print(f"Account check passed: @{username} ({account.get('id', user_id)}).")

        container = request_json(
            "POST",
            f"{user_id}/media",
            {
                "image_url": TEST_IMAGE_URL,
                "caption": "English Reading Room connection check.",
            },
        )
        container_id = str(container.get("id", ""))
        if not container_id:
            raise GraphError("Container creation returned no container ID.")
        print("Created an unpublished test media container; checking its status.")

        deadline = time.monotonic() + 600
        last_status = "UNKNOWN"
        while time.monotonic() < deadline:
            status = request_json(
                "GET",
                container_id,
                {"fields": "status_code,status"},
            )
            last_status = str(status.get("status_code", "UNKNOWN"))
            if last_status == "FINISHED":
                print("Test container status: FINISHED. It was not published.")
                return 0
            if last_status in {"ERROR", "EXPIRED"}:
                detail = status.get("status", "No status detail supplied.")
                raise GraphError(f"Test container status: {last_status}. {detail}")
            print(f"Test container status: {last_status}; waiting.")
            time.sleep(10)
        raise GraphError(f"Timed out while waiting for the test container; last status: {last_status}.")
    except GraphError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
