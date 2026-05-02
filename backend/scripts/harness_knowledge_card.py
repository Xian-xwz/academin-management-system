from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def request_json(method: str, url: str, *, token: str | None = None, body: dict | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login(base_url: str, username: str, password: str) -> str:
    data = request_json("POST", f"{base_url}/api/auth/login", body={"username": username, "password": password})
    return data["data"]["token"]


def parse_sse_line(raw: bytes) -> dict | None:
    line = raw.decode("utf-8", errors="replace").strip()
    if not line.startswith("data:"):
        return None
    return json.loads(line.removeprefix("data:").strip())


def run_stream(base_url: str, token: str, input_text: str, image_path: str | None) -> int:
    boundary = "----knowledge-card-harness-boundary"
    parts: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(value.encode("utf-8"))
        parts.append(b"\r\n")

    add_field("inputText", input_text)
    if image_path:
        path = Path(image_path)
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode())
        parts.append(b"Content-Type: image/png\r\n\r\n")
        parts.append(path.read_bytes())
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{base_url}/api/knowledge-cards/stream",
        data=b"".join(parts),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    card_id = 0
    with urllib.request.urlopen(req, timeout=240) as resp:
        for raw in resp:
            event = parse_sse_line(raw)
            if not event:
                continue
            print(json.dumps(event, ensure_ascii=False))
            if event.get("cardId"):
                card_id = int(event["cardId"])
            if event.get("event") in {"done", "error"}:
                break
    return card_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test knowledge card stream API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8081")
    parser.add_argument("--username", default="202211911001")
    parser.add_argument("--password", default="guangdong11")
    parser.add_argument("--text", default="RAG 是检索增强生成，先从知识库检索相关资料，再结合大模型生成回答。")
    parser.add_argument("--image")
    args = parser.parse_args()

    try:
        token = login(args.base_url, args.username, args.password)
        card_id = run_stream(args.base_url, token, args.text, args.image)
        if card_id:
            detail = request_json("GET", f"{args.base_url}/api/knowledge-cards/{card_id}", token=token)
            print(json.dumps(detail["data"], ensure_ascii=False)[:1200])
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
