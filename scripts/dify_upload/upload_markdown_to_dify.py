from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "knowledge" / "dify_upload"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "dify_upload_result.json"
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"

COMPLETED_STATUSES = {"completed", "success"}
FAILED_STATUSES = {"error", "failed"}
DEFAULT_EXCLUDE_KEYWORDS = ["广东海洋大学 2021 版本科"]
RATE_LIMIT_LOCK = Lock()
LAST_REQUEST_AT = 0.0
MIN_REQUEST_INTERVAL_SECONDS = 0.0


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_value(env: dict[str, str], key: str, default: str = "") -> str:
    return os.environ.get(key) or env.get(key) or default


def make_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def setup_request_rate_limit(requests_per_minute: int) -> None:
    global MIN_REQUEST_INTERVAL_SECONDS
    MIN_REQUEST_INTERVAL_SECONDS = 60 / requests_per_minute if requests_per_minute > 0 else 0


def wait_for_request_slot() -> None:
    global LAST_REQUEST_AT
    if MIN_REQUEST_INTERVAL_SECONDS <= 0:
        return
    with RATE_LIMIT_LOCK:
        now = time.time()
        wait_seconds = MIN_REQUEST_INTERVAL_SECONDS - (now - LAST_REQUEST_AT)
        if wait_seconds > 0:
            log(f"等待请求节流 {wait_seconds:.1f}s")
            time.sleep(wait_seconds)
        LAST_REQUEST_AT = time.time()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"generated_at": None, "items": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"generated_at": None, "items": []}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    temp_path.replace(path)


def collect_markdown_files(input_dir: Path, include: list[str], exclude: list[str], limit: int | None) -> list[Path]:
    files = sorted(path for path in input_dir.glob("*.md") if path.name.upper() != "README.MD")
    if include:
        keywords = [item.strip() for item in include if item.strip()]
        files = [path for path in files if any(keyword in path.name for keyword in keywords)]
    exclude_keywords = [item.strip() for item in [*DEFAULT_EXCLUDE_KEYWORDS, *exclude] if item.strip()]
    if exclude_keywords:
        files = [path for path in files if not any(keyword in path.name for keyword in exclude_keywords)]
    if limit is not None:
        files = files[:limit]
    return files


def request_json(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method=method)
    request.add_header("Authorization", f"Bearer {api_key}")
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "Mozilla/5.0 DifyKnowledgeUploader/1.0")
    if payload is not None:
        request.add_header("Content-Type", "application/json")

    try:
        wait_for_request_slot()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"URL error: {exc.reason}") from exc
    except OSError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def build_payload(path: Path, env: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": path.name,
        "text": path.read_text(encoding="utf-8"),
        "indexing_technique": args.indexing_technique,
        "doc_form": args.doc_form,
        "doc_language": args.doc_language,
        "process_rule": {"mode": args.process_mode},
    }

    embedding_model = env_value(env, "DIFY_EMBEDDING_MODEL")
    embedding_provider = env_value(env, "DIFY_EMBEDDING_MODEL_PROVIDER")
    if embedding_model:
        payload["embedding_model"] = embedding_model
    if embedding_provider:
        payload["embedding_model_provider"] = embedding_provider
    return payload


def create_document(path: Path, env: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    base_url = env_value(env, "DIFY_KNOWLEDGE_API_BASE", "https://api.dify.ai/v1")
    dataset_id = env_value(env, "DIFY_DATASET_ID")
    api_key = env_value(env, "DIFY_DATASET_API_KEY")
    url = make_url(base_url, f"/datasets/{dataset_id}/document/create-by-text")
    payload = build_payload(path, env, args)

    last_error = ""
    for attempt in range(1, args.max_retries + 1):
        try:
            log(f"开始上传：{path.name}（第 {attempt}/{args.max_retries} 次）")
            response = request_json("POST", url, api_key, payload=payload, timeout=args.timeout)
            document = response.get("document") or {}
            log(f"上传成功：{path.name}，document_id={document.get('id')}")
            return {
                "file": str(path.relative_to(PROJECT_ROOT)),
                "name": path.name,
                "document_id": document.get("id"),
                "batch": response.get("batch"),
                "upload_status": "success",
                "indexing_status": document.get("indexing_status"),
                "error": None,
                "attempts": attempt,
                "uploaded_at": datetime.now().isoformat(timespec="seconds"),
            }
        except RuntimeError as exc:
            last_error = str(exc)
            log(f"上传失败：{path.name}，第 {attempt}/{args.max_retries} 次，错误={last_error[:240]}")
            if is_non_retryable_config_error(last_error):
                return {
                    "file": str(path.relative_to(PROJECT_ROOT)),
                    "name": path.name,
                    "document_id": None,
                    "batch": None,
                    "upload_status": "config_error",
                    "indexing_status": None,
                    "error": last_error,
                    "attempts": attempt,
                    "uploaded_at": datetime.now().isoformat(timespec="seconds"),
                }
            if is_document_limit_error(last_error):
                return {
                    "file": str(path.relative_to(PROJECT_ROOT)),
                    "name": path.name,
                    "document_id": None,
                    "batch": None,
                    "upload_status": "document_limited",
                    "indexing_status": None,
                    "error": last_error,
                    "attempts": attempt,
                    "uploaded_at": datetime.now().isoformat(timespec="seconds"),
                }
            if args.stop_on_rate_limit and is_rate_limit_error(last_error):
                return {
                    "file": str(path.relative_to(PROJECT_ROOT)),
                    "name": path.name,
                    "document_id": None,
                    "batch": None,
                    "upload_status": "rate_limited",
                    "indexing_status": None,
                    "error": last_error,
                    "attempts": attempt,
                    "uploaded_at": datetime.now().isoformat(timespec="seconds"),
                }
            if attempt < args.max_retries:
                if is_rate_limit_error(last_error):
                    log(f"触发限流，等待 {args.rate_limit_cooldown}s 后重试")
                    time.sleep(args.rate_limit_cooldown)
                else:
                    retry_delay = min(args.retry_base_delay * attempt, 30)
                    log(f"等待 {retry_delay}s 后重试")
                    time.sleep(retry_delay)

    return {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "name": path.name,
        "document_id": None,
        "batch": None,
        "upload_status": "error",
        "indexing_status": None,
        "error": last_error,
        "attempts": args.max_retries,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
    }


def poll_batch(item: dict[str, Any], env: dict[str, str], args: argparse.Namespace) -> dict[str, Any]:
    batch = item.get("batch")
    if not batch or item.get("upload_status") != "success":
        return item

    base_url = env_value(env, "DIFY_KNOWLEDGE_API_BASE", "https://api.dify.ai/v1")
    dataset_id = env_value(env, "DIFY_DATASET_ID")
    api_key = env_value(env, "DIFY_DATASET_API_KEY")
    url = make_url(base_url, f"/datasets/{dataset_id}/documents/{batch}/indexing-status")
    deadline = time.time() + args.poll_timeout

    log(f"开始轮询索引：{item.get('name')}，batch={batch}")
    while time.time() < deadline:
        try:
            response = request_json("GET", url, api_key, timeout=args.timeout)
        except RuntimeError as exc:
            if is_rate_limit_error(str(exc)):
                log(f"轮询触发限流：{item.get('name')}，等待 {args.rate_limit_cooldown}s 后继续")
                time.sleep(args.rate_limit_cooldown)
                continue
            item["indexing_status"] = "poll_error"
            item["error"] = str(exc)
            log(f"轮询失败：{item.get('name')}，错误={item['error'][:240]}")
            return item

        records = response.get("data") or response.get("documents") or response.get("items") or []
        if isinstance(records, dict):
            records = [records]
        if not records:
            item["indexing_status"] = response.get("indexing_status") or item.get("indexing_status")
        else:
            statuses = [record.get("indexing_status") or record.get("status") for record in records]
            errors = [record.get("error") for record in records if record.get("error")]
            item["indexing_status"] = ",".join(status for status in statuses if status) or item.get("indexing_status")
            if errors:
                item["error"] = "; ".join(errors)

        status_text = str(item.get("indexing_status") or "").lower()
        log(f"索引状态：{item.get('name')} -> {item.get('indexing_status') or 'unknown'}")
        if any(status in status_text for status in COMPLETED_STATUSES | FAILED_STATUSES):
            item["indexed_at"] = datetime.now().isoformat(timespec="seconds")
            return item
        time.sleep(args.poll_interval)

    item["indexing_status"] = item.get("indexing_status") or "poll_timeout"
    item["error"] = item.get("error") or f"索引状态轮询超过 {args.poll_timeout} 秒"
    return item


def validate_config(env: dict[str, str]) -> None:
    missing = [key for key in ["DIFY_KNOWLEDGE_API_BASE", "DIFY_DATASET_API_KEY", "DIFY_DATASET_ID"] if not env_value(env, key)]
    if missing:
        raise SystemExit(f"缺少必要配置：{', '.join(missing)}。请先填写项目根目录 .env。")


def is_rate_limit_error(message: str) -> bool:
    normalized = message.lower()
    return "knowledge base request rate limit" in normalized or "rate limit" in normalized


def is_document_limit_error(message: str) -> bool:
    normalized = message.lower()
    return "number of documents has reached the limit" in normalized or "document" in normalized and "subscription" in normalized


def is_non_retryable_config_error(message: str) -> bool:
    normalized = message.lower()
    return "invalid_param" in normalized and ("provider" in normalized or "model" in normalized)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量上传 knowledge/dify_upload Markdown 到 Dify 知识库")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH), help="环境变量文件路径")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Markdown 文件目录")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="上传结果报告路径")
    parser.add_argument("--include", action="append", default=[], help="仅上传文件名包含该关键词的文件，可重复传入")
    parser.add_argument("--exclude", action="append", default=[], help="排除文件名包含该关键词的文件，可重复传入")
    parser.add_argument("--limit", type=int, default=None, help="最多上传前 N 个文件，适合试跑")
    parser.add_argument("--force", action="store_true", help="即使报告中已有成功记录，也重新上传")
    parser.add_argument("--dry-run", action="store_true", help="只列出将要上传的文件，不调用 API")
    parser.add_argument("--no-poll", action="store_true", help="只创建文档，不轮询索引状态")
    parser.add_argument("--concurrency", type=int, default=None, help="并发数，默认读取 DIFY_UPLOAD_CONCURRENCY")
    parser.add_argument("--max-retries", type=int, default=3, help="单文件最大重试次数")
    parser.add_argument("--retry-base-delay", type=int, default=5, help="重试基础等待秒数")
    parser.add_argument("--rate-limit-cooldown", type=int, default=120, help="触发 Dify 云端限流后的等待秒数")
    parser.add_argument("--stop-on-rate-limit", action="store_true", help="遇到 Dify 限流立即停止，避免继续产生失败记录")
    parser.add_argument("--knowledge-requests-per-minute", type=int, default=None, help="Dify 知识库请求速率上限，默认读取 DIFY_KNOWLEDGE_REQUESTS_PER_MINUTE")
    parser.add_argument("--timeout", type=int, default=90, help="单次 HTTP 超时秒数")
    parser.add_argument("--poll-interval", type=int, default=5, help="索引状态轮询间隔秒数")
    parser.add_argument("--poll-timeout", type=int, default=900, help="单文档索引轮询最大秒数")
    parser.add_argument("--indexing-technique", default="high_quality", choices=["high_quality", "economy"])
    parser.add_argument("--doc-form", default="text_model", choices=["text_model", "hierarchical_model", "qa_model"])
    parser.add_argument("--doc-language", default="Chinese")
    parser.add_argument("--process-mode", default="automatic", choices=["automatic", "custom", "hierarchical"])
    return parser.parse_args()


def main() -> None:
    configure_console_encoding()
    args = parse_args()
    env = load_env(Path(args.env_file))
    validate_config(env)
    requests_per_minute = args.knowledge_requests_per_minute or int(env_value(env, "DIFY_KNOWLEDGE_REQUESTS_PER_MINUTE", "10"))
    setup_request_rate_limit(requests_per_minute)

    input_dir = Path(args.input_dir)
    report_path = Path(args.report)
    report = read_json(report_path)
    previous_items = {item.get("file"): item for item in report.get("items", [])}

    files = collect_markdown_files(input_dir, args.include, args.exclude, args.limit)
    pending_files = []
    for path in files:
        rel = str(path.relative_to(PROJECT_ROOT))
        old = previous_items.get(rel)
        if old and old.get("upload_status") == "success" and not args.force:
            continue
        pending_files.append(path)

    log(f"待上传文件：{len(pending_files)} / 匹配文件：{len(files)} / 请求速率：{requests_per_minute} 次/分钟")
    if args.dry_run:
        for path in pending_files:
            log(path.name)
        return

    concurrency = args.concurrency or int(env_value(env, "DIFY_UPLOAD_CONCURRENCY", "3"))
    concurrency = max(1, min(concurrency, 8))
    log(f"并发数：{concurrency}；断点续传已启用，报告中 success 的文件会跳过")

    new_items: list[dict[str, Any]] = []
    if concurrency == 1:
        for index, path in enumerate(pending_files, start=1):
            log(f"处理进度：[{index}/{len(pending_files)}] {path.name}")
            item = create_document(path, env, args)
            if not args.no_poll:
                item = poll_batch(item, env, args)
            new_items.append(item)
            log(f"处理完成：[{index}/{len(pending_files)}] {item['name']} -> {item['upload_status']} / {item.get('indexing_status')}")

            merged = merge_items(previous_items, new_items)
            write_json(report_path, build_report(merged))
            log(f"已写入报告：{report_path.relative_to(PROJECT_ROOT)}")
            if item.get("upload_status") == "rate_limited":
                log("检测到 Dify 云端限流，已停止本轮上传。稍后重新执行同一命令即可断点续传。")
                break
            if item.get("upload_status") == "document_limited":
                log("检测到 Dify 文档数量已达订阅上限，已停止上传。需要删除旧文档、升级额度或合并 Markdown 后再继续。")
                break
            if item.get("upload_status") == "config_error":
                log("检测到 Dify 模型/供应商配置错误，已停止上传。请修正 .env 或 Dify 控制台模型配置后再继续。")
                break
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(create_document, path, env, args): path for path in pending_files}
            for index, future in enumerate(as_completed(futures), start=1):
                item = future.result()
                if not args.no_poll:
                    item = poll_batch(item, env, args)
                new_items.append(item)
                log(f"处理完成：[{index}/{len(pending_files)}] {item['name']} -> {item['upload_status']} / {item.get('indexing_status')}")

                merged = merge_items(previous_items, new_items)
                write_json(report_path, build_report(merged))
                log(f"已写入报告：{report_path.relative_to(PROJECT_ROOT)}")
                if item.get("upload_status") == "rate_limited":
                    log("检测到 Dify 云端限流，已停止本轮上传。稍后重新执行同一命令即可断点续传。")
                    break
                if item.get("upload_status") == "document_limited":
                    log("检测到 Dify 文档数量已达订阅上限，已停止上传。需要删除旧文档、升级额度或合并 Markdown 后再继续。")
                    break
                if item.get("upload_status") == "config_error":
                    log("检测到 Dify 模型/供应商配置错误，已停止上传。请修正 .env 或 Dify 控制台模型配置后再继续。")
                    break

    merged = merge_items(previous_items, new_items)
    final_report = build_report(merged)
    write_json(report_path, final_report)
    log(
        "完成："
        f"success={final_report['summary']['upload_success']}, "
        f"error={final_report['summary']['upload_error']}, "
        f"indexed_completed={final_report['summary']['indexing_completed']}"
    )


def merge_items(previous_items: dict[str, dict[str, Any]], new_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = dict(previous_items)
    for item in new_items:
        merged[item["file"]] = item
    return sorted(merged.values(), key=lambda item: item.get("file", ""))


def build_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    upload_success = sum(1 for item in items if item.get("upload_status") == "success")
    upload_error = sum(1 for item in items if item.get("upload_status") == "error")
    rate_limited = sum(1 for item in items if item.get("upload_status") == "rate_limited")
    document_limited = sum(1 for item in items if item.get("upload_status") == "document_limited")
    config_error = sum(1 for item in items if item.get("upload_status") == "config_error")
    indexing_completed = sum(
        1 for item in items if any(status in str(item.get("indexing_status", "")).lower() for status in COMPLETED_STATUSES)
    )
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_records": len(items),
            "upload_success": upload_success,
            "upload_error": upload_error,
            "rate_limited": rate_limited,
            "document_limited": document_limited,
            "config_error": config_error,
            "indexing_completed": indexing_completed,
        },
        "items": items,
    }


if __name__ == "__main__":
    main()
