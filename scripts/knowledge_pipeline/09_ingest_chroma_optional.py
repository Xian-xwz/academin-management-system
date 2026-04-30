from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import DIFY_UPLOAD_DIR, KNOWLEDGE_DIR, PROJECT_ROOT, read_text


def parse_metadata(text: str) -> dict[str, str]:
    metadata = {}
    for key, field in [("major_name", "专业名称"), ("major_code", "专业代码"), ("doc_type", "文档类型")]:
        match = re.search(rf"-\s*{field}[:：]\s*(.+)", text)
        metadata[key] = match.group(1).strip() if match else ""
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="可选：将 Dify 上传 Markdown 写入 Chroma 本地向量库")
    parser.add_argument("--persist-dir", default=str(KNOWLEDGE_DIR / "chroma_db"), help="Chroma 持久化目录")
    parser.add_argument("--collection", default="academic_knowledge", help="Chroma collection 名称")
    args = parser.parse_args()

    try:
        import chromadb
    except ModuleNotFoundError as exc:
        raise SystemExit("未安装 chromadb，跳过可选 Chroma 写入。需要时先安装：pip install chromadb") from exc

    paths = sorted(path for path in DIFY_UPLOAD_DIR.glob("*.md") if path.name.upper() != "README.MD")
    client = chromadb.PersistentClient(path=args.persist_dir)
    collection = client.get_or_create_collection(args.collection)

    ids = []
    documents = []
    metadatas = []
    for path in paths:
        text = read_text(path)
        rel_path = str(path.relative_to(PROJECT_ROOT))
        ids.append(rel_path.replace("\\", "/"))
        documents.append(text)
        metadatas.append({**parse_metadata(text), "source_file": rel_path})

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Chroma 写入完成：{len(ids)} 个文档，目录：{Path(args.persist_dir)}，collection：{args.collection}")


if __name__ == "__main__":
    main()
