"""Create and optionally publish an Instagram media container."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v27.0")
GRAPH_BASE = f"https://graph.facebook.com/{API_VERSION}"
RETRY_DELAYS = (2, 4, 8)
POLL_SECONDS = 10
POLL_TIMEOUT = 600


class PublishError(RuntimeError):
    pass


class GraphClient:
    def __init__(self, token: str):
        if not token:
            raise PublishError("IG_TOKEN is missing.")
        self.token = token

    def request(self, method: str, path: str, params: dict[str, str] | None = None) -> dict:
        url = f"{GRAPH_BASE}/{path.lstrip('/')}"
        payload = None
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        if params:
            encoded = urllib.parse.urlencode(params)
            if method == "GET":
                url = f"{url}?{encoded}"
            else:
                payload = encoded.encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(url, data=payload, headers=headers, method=method)

        for attempt, delay in enumerate((*RETRY_DELAYS, None)):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    result = json.loads(response.read().decode("utf-8"))
                if not isinstance(result, dict):
                    raise PublishError("Graph API returned an unexpected response.")
                return result
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if retryable and delay is not None:
                    print(f"Temporary Graph API response (HTTP {error.code}); retrying in {delay}s.")
                    time.sleep(delay)
                    continue
                try:
                    details = json.loads(error.read().decode("utf-8")).get("error", {})
                except (ValueError, AttributeError):
                    details = {}
                code = details.get("code", "unknown")
                raise PublishError(f"Graph API request failed (HTTP {error.code}, code {code}).") from None
            except (urllib.error.URLError, TimeoutError) as error:
                if delay is not None:
                    print(f"Temporary network failure; retrying in {delay}s.")
                    time.sleep(delay)
                    continue
                reason = error.reason if hasattr(error, "reason") else "timeout"
                raise PublishError(f"Network request failed ({reason}).") from None
        raise PublishError("Graph API request failed after retries.")


def load_content(path: Path) -> dict:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PublishError(f"Could not read content file: {error}") from None
    kind = str(content.get("kind", "")).upper()
    if kind not in {"REELS", "CAROUSEL", "IMAGE", "STORIES"}:
        raise PublishError("Content kind must be REELS, CAROUSEL, or IMAGE.")
    if kind != "STORIES" and not str(content.get("caption", "")).strip():
        raise PublishError("Caption is required.")
    if kind == "REELS" and not str(content.get("video_url", "")).startswith("https://"):
        raise PublishError("A public HTTPS video_url is required for a Reel.")
    if kind == "IMAGE" and not str(content.get("image_url", "")).startswith("https://"):
        raise PublishError("A public HTTPS image_url is required for an image.")
    if kind == "STORIES" and not (str(content.get("image_url", "")).startswith("https://") or str(content.get("video_url", "")).startswith("https://")):
        raise PublishError("A public HTTPS image_url or video_url is required for a story.")
    if kind == "CAROUSEL":
        slides = content.get("slides")
        if not isinstance(slides, list) or not 2 <= len(slides) <= 10:
            raise PublishError("A carousel must contain between 2 and 10 slides.")
        if any(not str(slide).startswith("https://") for slide in slides):
            raise PublishError("Every carousel slide needs a public HTTPS URL.")
    return content


def wait_until_finished(client: GraphClient, container_id: str) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        status = client.request("GET", container_id, {"fields": "status_code,status"})
        code = str(status.get("status_code", "UNKNOWN"))
        print(f"Container {container_id}: {code}.")
        if code == "FINISHED":
            return status
        if code in {"ERROR", "EXPIRED"}:
            raise PublishError(f"Container {container_id} ended with status {code}.")
        time.sleep(POLL_SECONDS)
    raise PublishError(f"Container {container_id} did not finish within {POLL_TIMEOUT} seconds.")


def create_image(client: GraphClient, user_id: str, image_url: str, caption: str, is_item: bool = False) -> str:
    params = {"image_url": image_url}
    if is_item:
        params["is_carousel_item"] = "true"
    else:
        params["caption"] = caption
    response = client.request("POST", f"{user_id}/media", params)
    container_id = str(response.get("id", ""))
    if not container_id:
        raise PublishError("Image container creation returned no ID.")
    return container_id


def create_container(client: GraphClient, user_id: str, content: dict) -> str:
    kind = str(content["kind"]).upper()
    caption = str(content["caption"])
    if kind == "REELS":
        response = client.request("POST", f"{user_id}/media", {
            "media_type": "REELS",
            "video_url": content["video_url"],
            "caption": caption,
            "share_to_feed": "true",
            **({"cover_url": content["cover_url"]} if content.get("cover_url") else
               {"thumb_offset": str(int(content["thumb_offset"]))} if content.get("thumb_offset") else {}),
        })
        container_id = str(response.get("id", ""))
        if not container_id:
            raise PublishError("Reel container creation returned no ID.")
        return container_id
    if kind == "IMAGE":
        return create_image(client, user_id, content["image_url"], caption)
    if kind == "STORIES":
        media = {"video_url": content["video_url"]} if content.get("video_url") else {"image_url": content["image_url"]}
        response = client.request("POST", f"{user_id}/media", {"media_type": "STORIES", **media})
        container_id = str(response.get("id", ""))
        if not container_id:
            raise PublishError("Story container creation returned no ID.")
        return container_id

    child_ids = []
    for index, image_url in enumerate(content["slides"], start=1):
        child_id = create_image(client, user_id, image_url, caption, is_item=True)
        print(f"Created carousel item {index}/{len(content['slides'])}.")
        wait_until_finished(client, child_id)
        child_ids.append(child_id)
    response = client.request("POST", f"{user_id}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": caption,
    })
    container_id = str(response.get("id", ""))
    if not container_id:
        raise PublishError("Carousel container creation returned no ID.")
    return container_id


def run(content_path: Path, dry_run: bool) -> int:
    content = load_content(content_path)
    if dry_run:
        print(f"DRY_RUN=1: validated {content['kind']} draft '{content_path.name}'.")
        print("No Graph API requests were sent.")
        return 0

    user_id = os.environ.get("IG_USER_ID", "").strip()
    if not user_id:
        raise PublishError("IG_USER_ID is missing.")
    client = GraphClient(os.environ.get("IG_TOKEN", ""))
    print(f"Creating {content['kind']} container for account {user_id}.")
    container_id = create_container(client, user_id, content)
    wait_until_finished(client, container_id)

    response = client.request("POST", f"{user_id}/media_publish", {"creation_id": container_id})
    media_id = response.get("id")
    print(f"Published successfully; Instagram media ID: {media_id}.")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python publish/publish.py <content.json>", file=sys.stderr)
        return 2
    dry_run = os.environ.get("DRY_RUN", "1").strip().lower() not in {"0", "false", "no"}
    try:
        return run(Path(sys.argv[1]), dry_run)
    except PublishError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
