from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "docs" / "人才培养方案"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
MARKDOWN_DIR = KNOWLEDGE_DIR / "markdown"
MAJORS_RAW_DIR = MARKDOWN_DIR / "majors_raw"
WIKI_DIR = KNOWLEDGE_DIR / "wiki"
WIKI_MAJORS_DIR = WIKI_DIR / "majors"
DIFY_UPLOAD_DIR = KNOWLEDGE_DIR / "dify_upload"
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"

TARGET_MAJORS = {"计算机科学与技术", "软件工程", "数据科学与大数据技术"}

MAJOR_HEADING_RE = re.compile(r"^#\s*(.+?专业人才培养方案)\s*$", re.MULTILINE)
SECTION_RE = re.compile(r"^(?:#\s*)?([一二三四五六七八九十]+、.+?)\s*$", re.MULTILINE)
TABLE_RE = re.compile(r"<table>.*?</table>", re.DOTALL)
CODE_RE = re.compile(r"^[a-zA-Z]?\d{6,}$")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def ensure_dirs() -> None:
    for path in [
        MARKDOWN_DIR,
        MAJORS_RAW_DIR,
        WIKI_MAJORS_DIR,
        WIKI_DIR / "concepts",
        WIKI_DIR / "summaries",
        DIFY_UPLOAD_DIR,
        DATA_DIR,
        REPORTS_DIR,
        SCHEMAS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"}:
            self._cell = []
            self._in_cell = True

    def handle_data(self, data: str) -> None:
        if self._in_cell and self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(normalize_text("".join(self._cell)))
            self._cell = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            if any(cell for cell in self._row):
                self.rows.append(self._row)
            self._row = None


def parse_table(html: str) -> list[list[str]]:
    parser = TableParser()
    parser.feed(html)
    return parser.rows


def rows_to_markdown(rows: list[list[str]], max_rows: int | None = None) -> str:
    if not rows:
        return ""
    rows = rows[:max_rows] if max_rows else rows
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    header = padded[0]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for row in padded[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


@dataclass
class SourceFile:
    path: Path
    first_page: int
    majors: list[dict[str, Any]]


def first_page_number(content_json: Path) -> int:
    def walk(obj: Any) -> int | None:
        if isinstance(obj, dict):
            if "page_number_content" in obj:
                text = "".join(
                    item.get("content", "") for item in obj.get("page_number_content", []) if isinstance(item, dict)
                )
                match = NUMBER_RE.search(text)
                if match:
                    return int(float(match.group()))
            for value in obj.values():
                found = walk(value)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = walk(item)
                if found is not None:
                    return found
        return None

    if not content_json.exists():
        return 999999
    try:
        data = json.loads(read_text(content_json))
        return walk(data) or 999999
    except Exception:
        return 999999


def find_sources() -> list[SourceFile]:
    sources: list[SourceFile] = []
    for full_md in SOURCE_ROOT.glob("*/full.md"):
        lines = read_text(full_md).splitlines()
        majors = []
        for idx, line in enumerate(lines, start=1):
            match = MAJOR_HEADING_RE.match(line)
            if match:
                major_name = match.group(1).replace("专业人才培养方案", "")
                if major_name.startswith("广东海洋大学"):
                    continue
                majors.append({"major_name": major_name, "line": idx})
        page = first_page_number(full_md.parent / "content_list_v2.json")
        sources.append(SourceFile(path=full_md, first_page=page, majors=majors))
    return sorted(sources, key=lambda item: (item.first_page, str(item.path)))


def build_inventory() -> dict[str, Any]:
    ensure_dirs()
    sources = find_sources()
    inventory = {
        "source_root": str(SOURCE_ROOT),
        "source_count": len(sources),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sources": [
            {
                "path": str(source.path.relative_to(PROJECT_ROOT)),
                "first_page": source.first_page,
                "sha256": file_sha256(source.path),
                "mtime": datetime.fromtimestamp(source.path.stat().st_mtime).isoformat(timespec="seconds"),
                "majors": source.majors,
            }
            for source in sources
        ],
    }
    write_json(MARKDOWN_DIR / "source_index.json", inventory)
    lines = [
        "# MinerU 来源清单",
        "",
        f"- 来源目录：`{SOURCE_ROOT}`",
        f"- full.md 数量：{len(sources)}",
        "",
    ]
    for source in sources:
        lines.append(f"## {source.path.parent.name}")
        lines.append(f"- 文件：`{source.path.relative_to(PROJECT_ROOT)}`")
        lines.append(f"- 起始页码：{source.first_page}")
        lines.append(f"- 专业数量：{len(source.majors)}")
        for major in source.majors:
            lines.append(f"  - {major['major_name']}（行 {major['line']}）")
        lines.append("")
    write_text(MARKDOWN_DIR / "source_inventory.md", "\n".join(lines))
    write_text(REPORTS_DIR / "source_inventory_report.md", "\n".join(lines))
    return inventory


def merge_full_markdown() -> Path:
    ensure_dirs()
    sources = find_sources()
    parts = []
    for source in sources:
        rel = source.path.relative_to(PROJECT_ROOT)
        parts.append(f"\n\n<!-- source: {rel}; first_page: {source.first_page} -->\n\n")
        parts.append(read_text(source.path))
    master = "\n".join(parts).strip() + "\n"
    master_path = MARKDOWN_DIR / "master.md"
    write_text(master_path, master)
    return master_path


def split_by_major() -> list[dict[str, Any]]:
    ensure_dirs()
    master_path = MARKDOWN_DIR / "master.md"
    if not master_path.exists():
        merge_full_markdown()
    text = read_text(master_path)
    matches = list(MAJOR_HEADING_RE.finditer(text))
    majors: list[dict[str, Any]] = []
    if matches and matches[0].start() > 0:
        write_text(WIKI_DIR / "summaries" / "未归属片段.md", text[: matches[0].start()].strip() + "\n")
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = match.group(1)
        major_name = heading.replace("专业人才培养方案", "")
        if major_name.startswith("广东海洋大学"):
            continue
        content = text[start:end].strip() + "\n"
        raw_path = MAJORS_RAW_DIR / f"{slugify(major_name)}.md"
        write_text(raw_path, content)
        majors.append({"major_name": major_name, "raw_path": str(raw_path.relative_to(PROJECT_ROOT))})
    write_json(MARKDOWN_DIR / "major_index.json", majors)
    lines = ["# 专业切分校验报告", "", f"- 专业数量：{len(majors)}", ""]
    for item in majors:
        lines.append(f"- {item['major_name']}：`{item['raw_path']}`")
    write_text(REPORTS_DIR / "split_validation_report.md", "\n".join(lines) + "\n")
    return majors


def extract_metadata(content: str, major_name: str) -> dict[str, Any]:
    def find(pattern: str) -> str:
        match = re.search(pattern, content)
        return normalize_text(match.group(1)) if match else ""

    return {
        "major_code": find(r"专业代码[:：]\s*([A-Za-z0-9]+)"),
        "major_name": major_name,
        "major_category": find(r"专业类[:：]\s*(.+)"),
        "degree": find(r"授予学位[:：]\s*(.+)"),
    }


def split_sections(content: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(content))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections[match.group(1)] = content[start:end].strip()
    return sections


def find_section(sections: dict[str, str], keyword: str) -> str:
    for title, content in sections.items():
        if keyword in title:
            return content
    return ""


def first_table_rows(section: str) -> list[list[str]]:
    match = TABLE_RE.search(section)
    return parse_table(match.group(0)) if match else []


def first_number(cells: list[str]) -> float | None:
    for cell in cells:
        match = NUMBER_RE.search(cell)
        if match:
            return float(match.group())
    return None


def summarize_credit_structure(rows: list[list[str]]) -> tuple[dict[str, Any], str]:
    data = {
        "total_credits": None,
        "theory_credits": None,
        "practice_credits": None,
        "general_required_credits": None,
        "general_elective_credits": None,
        "major_basic_credits": None,
        "major_required_credits": None,
        "major_limited_elective_credits": None,
        "major_optional_credits": None,
    }
    markdown_lines = ["## 学分结构摘要", ""]
    current_system = ""
    current_module = ""
    theory_subtotal_seen = False
    for row in rows[1:]:
        joined = " ".join(row)
        compact_joined = re.sub(r"\s+", "", joined)
        for cell in row:
            compact_cell = re.sub(r"\s+", "", cell)
            if "理论教学" in compact_cell:
                current_system = "理论教学"
            elif "实践教学" in compact_cell:
                current_system = "实践教学"
            if "通识教育课" in compact_cell:
                current_module = "通识教育课"
            elif "专业基础课" in compact_cell:
                current_module = "专业基础课"
            elif compact_cell == "专业课" or "专业课" in compact_cell and len(compact_cell) <= 8:
                current_module = "专业课"
            elif "思想政治理论课" in compact_cell:
                current_module = "思想政治理论课"

        nums = [float(match.group()) for match in NUMBER_RE.finditer(joined)]
        credit = nums[0] if nums else None
        if "合计" in compact_joined:
            data["total_credits"] = credit
            continue
        if "小计" in compact_joined:
            if current_system == "理论教学" and not theory_subtotal_seen:
                data["theory_credits"] = credit
                theory_subtotal_seen = True
            elif current_system == "实践教学":
                data["practice_credits"] = credit
            continue

        if current_system == "理论教学" and current_module == "通识教育课" and "必修" in compact_joined:
            data["general_required_credits"] = credit
        elif current_system == "理论教学" and current_module == "通识教育课" and ("选修" in compact_joined or "任选" in compact_joined):
            data["general_elective_credits"] = credit
        elif current_system == "理论教学" and current_module == "专业基础课":
            data["major_basic_credits"] = credit
        elif current_system == "理论教学" and current_module == "专业课" and "必修" in compact_joined:
            data["major_required_credits"] = credit
        elif current_system == "理论教学" and current_module == "专业课" and "限选" in compact_joined:
            data["major_limited_elective_credits"] = credit
        elif current_system == "理论教学" and current_module == "专业课" and "专业任选" in compact_joined:
            data["major_optional_credits"] = credit

    for label, key in [
        ("总学分", "total_credits"),
        ("理论教学", "theory_credits"),
        ("实践教学", "practice_credits"),
        ("通识教育必修", "general_required_credits"),
        ("通识教育选修", "general_elective_credits"),
        ("专业基础课", "major_basic_credits"),
        ("专业必修", "major_required_credits"),
        ("专业限选", "major_limited_elective_credits"),
        ("专业任选", "major_optional_credits"),
    ]:
        value = data.get(key)
        markdown_lines.append(f"- {label}：{value if value is not None else '待人工复核'} 学分")
    return data, "\n".join(markdown_lines)


def course_module_from_text(text: str, fallback: str) -> str:
    for keyword in ["思想政治理论课", "通识教育课", "专业基础课", "专业课", "实践教学", "通识实践", "教学实验", "课程与专业实习", "毕业实习"]:
        if keyword in text:
            return keyword
    return fallback


def extract_courses_from_rows(rows: list[list[str]], major_code: str, source_file: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    courses: list[dict[str, Any]] = []
    practices: list[dict[str, Any]] = []
    current_module = ""
    current_type = ""
    for row in rows[1:]:
        joined = " ".join(row)
        current_module = course_module_from_text(joined, current_module)
        if "必修" in joined:
            current_type = "必修"
        elif "限选" in joined:
            current_type = "限选"
        elif "专业任选" in joined or "任选" in joined:
            current_type = "专业任选"
        elif "选修" in joined:
            current_type = "选修"

        for idx, cell in enumerate(row):
            if CODE_RE.match(cell):
                name = row[idx + 1] if idx + 1 < len(row) else ""
                credits = first_number(row[idx + 2 : idx + 3]) if idx + 2 < len(row) else None
                hours = first_number(row[idx + 3 : idx + 4]) if idx + 3 < len(row) else None
                record = {
                    "course_code": cell,
                    "course_name": name,
                    "major_code": major_code,
                    "module": current_module,
                    "course_type": current_type,
                    "credits": credits,
                    "hours": hours,
                    "lecture_hours": None,
                    "practice_hours": None,
                    "semester": "",
                    "assessment": "",
                    "remark": "",
                    "source_file": source_file,
                    "needs_review": credits is None or not name,
                }
                if cell.lower().startswith("j"):
                    practices.append(
                        {
                            "practice_code": cell,
                            "practice_name": name,
                            "major_code": major_code,
                            "module": current_module,
                            "credits": credits,
                            "weeks": None,
                            "semester": "",
                            "organization": "",
                            "source_file": source_file,
                            "needs_review": credits is None or not name,
                        }
                    )
                else:
                    courses.append(record)
                break
    return courses, practices


def build_major_outputs() -> dict[str, Any]:
    ensure_dirs()
    major_index = json.loads(read_text(MARKDOWN_DIR / "major_index.json")) if (MARKDOWN_DIR / "major_index.json").exists() else split_by_major()
    majors_json: list[dict[str, Any]] = []
    grad_json: list[dict[str, Any]] = []
    courses_json: list[dict[str, Any]] = []
    practice_json: list[dict[str, Any]] = []
    field_report: list[dict[str, Any]] = []

    for item in major_index:
        major_name = item["major_name"]
        raw_path = PROJECT_ROOT / item["raw_path"]
        content = read_text(raw_path)
        metadata = extract_metadata(content, major_name)
        major_code = metadata["major_code"] or f"UNKNOWN_{len(majors_json)+1:03d}"
        safe_major = slugify(major_name)
        major_dir = WIKI_MAJORS_DIR / safe_major
        sections = split_sections(content)
        overview = "\n\n".join(
            part
            for part in [
                f"# {major_name}专业\n",
                "## 基本信息\n"
                f"- 专业名称：{major_name}\n"
                f"- 专业代码：{metadata['major_code'] or '待人工复核'}\n"
                f"- 专业类：{metadata['major_category'] or '待人工复核'}\n"
                f"- 授予学位：{metadata['degree'] or '待人工复核'}\n",
                find_section(sections, "专业培养目标"),
                find_section(sections, "毕业要求")[:3000],
                "## 来源\n"
                f"- 原始切分文件：`{item['raw_path']}`\n",
            ]
            if part
        )

        structure_section = find_section(sections, "课程结构比例表")
        structure_rows = first_table_rows(structure_section)
        credits, credit_md = summarize_credit_structure(structure_rows)
        credit_page = "\n\n".join(
            [
                f"# {major_name} - 毕业要求与学分结构",
                context_header(major_name, metadata, "毕业要求与学分结构"),
                credit_md,
                "## 课程结构比例表（简化表）",
                rows_to_markdown(structure_rows, max_rows=30),
            ]
        )

        course_section = find_section(sections, "课程设置")
        course_tables = [parse_table(match.group(0)) for match in TABLE_RE.finditer(course_section)]
        all_courses: list[dict[str, Any]] = []
        all_practices: list[dict[str, Any]] = []
        for rows in course_tables:
            c, p = extract_courses_from_rows(rows, major_code, f"knowledge/wiki/majors/{safe_major}/02_课程设置.md")
            all_courses.extend(c)
            all_practices.extend(p)
        course_summary = build_course_summary(major_name, metadata, all_courses)

        practice_section = find_section(sections, "实践教学")
        practice_tables = [parse_table(match.group(0)) for match in TABLE_RE.finditer(practice_section)]
        for rows in practice_tables:
            c, p = extract_courses_from_rows(rows, major_code, f"knowledge/wiki/majors/{safe_major}/03_实践教学.md")
            all_practices.extend(p)
        practice_summary = build_practice_summary(major_name, metadata, all_practices)

        matrix = find_section(sections, "关联度矩阵")
        matrix_page = "\n\n".join(
            [
                f"# {major_name} - 课程体系矩阵",
                context_header(major_name, metadata, "课程体系矩阵"),
                "本页面来自毕业要求与课程体系关联度矩阵。内容较长，Dify 主知识库可按效果选择是否上传。",
                rows_to_markdown(first_table_rows(matrix), max_rows=80) if matrix else "未识别到矩阵表。",
            ]
        )

        write_text(major_dir / "README.md", overview)
        write_text(major_dir / "00_专业总览.md", overview)
        write_text(major_dir / "01_毕业要求与学分结构.md", credit_page)
        write_text(major_dir / "02_课程设置.md", course_summary)
        write_text(major_dir / "03_实践教学.md", practice_summary)
        write_text(major_dir / "04_课程体系矩阵.md", matrix_page)

        dify_files = {
            "00_专业总览": overview,
            "01_毕业要求与学分结构": credit_page,
            "02_课程设置": course_summary,
            "03_实践教学": practice_summary,
            "04_课程体系矩阵": matrix_page,
        }
        for suffix, body in dify_files.items():
            write_text(DIFY_UPLOAD_DIR / f"{safe_major}_{suffix}.md", ensure_dify_context(body, major_name, metadata, suffix))

        majors_json.append({**metadata, "source_file": f"knowledge/wiki/majors/{safe_major}/README.md", "needs_review": not metadata["major_code"]})
        grad_json.append(
            {
                "major_code": major_code,
                "major_name": major_name,
                **credits,
                "source_file": f"knowledge/wiki/majors/{safe_major}/01_毕业要求与学分结构.md",
                "needs_review": any(value is None for value in credits.values()),
            }
        )
        courses_json.extend(all_courses)
        practice_json.extend(all_practices)
        field_report.append(
            {
                "major_name": major_name,
                "major_code": major_code,
                "has_total_credits": credits["total_credits"] is not None,
                "course_count": len(all_courses),
                "practice_count": len(all_practices),
                "needs_review": (not metadata["major_code"]) or any(value is None for value in credits.values()),
                "is_target_major": major_name in TARGET_MAJORS,
            }
        )

    write_json(DATA_DIR / "majors.json", majors_json)
    write_json(DATA_DIR / "graduation_requirements.json", grad_json)
    write_json(DATA_DIR / "courses.json", courses_json)
    write_json(DATA_DIR / "practice_courses.json", practice_json)
    write_json(REPORTS_DIR / "field_validation_report.json", field_report)
    write_json(REPORTS_DIR / "dify_upload_manifest.json", build_dify_manifest())
    build_reports(field_report)
    return {
        "majors": len(majors_json),
        "courses": len(courses_json),
        "practices": len(practice_json),
        "review_count": sum(1 for item in field_report if item["needs_review"]),
    }


def context_header(major_name: str, metadata: dict[str, Any], doc_type: str) -> str:
    return (
        f"- 专业名称：{major_name}\n"
        f"- 专业代码：{metadata.get('major_code') or '待人工复核'}\n"
        f"- 专业类：{metadata.get('major_category') or '待人工复核'}\n"
        f"- 授予学位：{metadata.get('degree') or '待人工复核'}\n"
        f"- 文档类型：{doc_type}\n"
        "- 来源：广东海洋大学2021版本科专业人才培养方案（上册）"
    )


def ensure_dify_context(body: str, major_name: str, metadata: dict[str, Any], doc_type: str) -> str:
    if "- 专业名称：" in body[:500] and "- 文档类型：" in body[:500]:
        return body
    return f"# {major_name} - {doc_type}\n\n{context_header(major_name, metadata, doc_type)}\n\n{body}"


def build_course_summary(major_name: str, metadata: dict[str, Any], courses: list[dict[str, Any]]) -> str:
    lines = [f"# {major_name} - 课程设置", "", context_header(major_name, metadata, "课程设置"), "", "## 课程清单摘要", ""]
    if not courses:
        lines.append("未自动识别到课程清单，需人工复核。")
        return "\n".join(lines)
    lines.append("| 课程编号 | 课程名称 | 模块 | 类型 | 学分 | 学时 |")
    lines.append("|---|---|---|---|---|---|")
    for item in courses:
        lines.append(
            f"| {item['course_code']} | {item['course_name']} | {item['module']} | {item['course_type']} | {item['credits'] or ''} | {item['hours'] or ''} |"
        )
    return "\n".join(lines)


def build_practice_summary(major_name: str, metadata: dict[str, Any], practices: list[dict[str, Any]]) -> str:
    lines = [f"# {major_name} - 实践教学", "", context_header(major_name, metadata, "实践教学"), "", "## 实践教学清单", ""]
    if not practices:
        lines.append("未自动识别到实践教学清单，需人工复核。")
        return "\n".join(lines)
    lines.append("| 编号 | 实践环节 | 模块 | 学分 | 学期 |")
    lines.append("|---|---|---|---|---|")
    for item in practices:
        lines.append(f"| {item['practice_code']} | {item['practice_name']} | {item['module']} | {item['credits'] or ''} | {item['semester']} |")
    return "\n".join(lines)


def build_dify_manifest() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(DIFY_UPLOAD_DIR.glob("*.md")):
        if path.name.upper() == "README.MD":
            continue
        size = path.stat().st_size
        text = read_text(path)[:800]
        major = re.search(r"专业名称[:：]\s*(.+)", text)
        doc_type = re.search(r"文档类型[:：]\s*(.+)", text)
        rows.append(
            {
                "file": str(path.relative_to(PROJECT_ROOT)),
                "size_bytes": size,
                "size_kb": round(size / 1024, 2),
                "major_name": normalize_text(major.group(1)) if major else "",
                "doc_type": normalize_text(doc_type.group(1)) if doc_type else "",
                "under_200kb": size < 200 * 1024,
                "needs_split": size > 500 * 1024,
            }
        )
    return rows


def build_reports(field_report: list[dict[str, Any]]) -> None:
    manifest = build_dify_manifest()
    lines = [
        "# 知识库流水线处理报告",
        "",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 专业数量：{len(field_report)}",
        f"- 待复核专业数量：{sum(1 for item in field_report if item['needs_review'])}",
        f"- Dify 上传文件数量：{len(manifest)}",
        "",
        "## 重点专业校验",
        "",
    ]
    for item in field_report:
        if item["is_target_major"]:
            lines.append(
                f"- {item['major_name']}：课程 {item['course_count']} 条，实践 {item['practice_count']} 条，"
                f"总学分字段={'有' if item['has_total_credits'] else '缺失'}，needs_review={item['needs_review']}"
            )
    lines.extend(["", "## Dify 上传文件大小异常", ""])
    oversized = [item for item in manifest if item["needs_split"]]
    if oversized:
        for item in oversized:
            lines.append(f"- `{item['file']}`：{item['size_kb']} KB")
    else:
        lines.append("- 无超过 500KB 的待拆分文件。")
    write_text(REPORTS_DIR / "knowledge_pipeline_report.md", "\n".join(lines) + "\n")

    qa_lines = [
        "# Dify 问答回归测试清单",
        "",
        "上传 `knowledge/dify_upload/` 后，在 Dify 控制台逐条测试并记录结果。",
        "",
        "| 问题 | 期望命中专业 | 期望答案要点 | 实际结果 | 是否通过 |",
        "|---|---|---|---|---|",
        "| 计算机科学与技术专业毕业总学分是多少？ | 计算机科学与技术 | 总学分、理论/实践学分 |  |  |",
        "| 软件工程专业实践教学需要多少学分？ | 软件工程 | 实践教学学分 |  |  |",
        "| 数据科学与大数据技术专业有哪些专业基础课？ | 数据科学与大数据技术 | 专业基础课程列表 |  |  |",
        "| 通识选修课最低要求是多少？ | 任一专业 | 通识选修学分与说明 |  |  |",
    ]
    write_text(PROJECT_ROOT / "plan" / "Dify问答测试清单.md", "\n".join(qa_lines) + "\n")
    write_text(REPORTS_DIR / "dify_qa_regression_report.md", "\n".join(qa_lines) + "\n")


def validate_outputs() -> dict[str, Any]:
    graduation_path = DATA_DIR / "graduation_requirements.json"
    graduation = json.loads(read_text(graduation_path)) if graduation_path.exists() else []
    missing_total = [item for item in graduation if item.get("total_credits") is None]
    manifest = build_dify_manifest()
    oversized = [item for item in manifest if item.get("needs_split")]
    result = {
        "graduation_records": len(graduation),
        "missing_total_credits": len(missing_total),
        "dify_upload_files": len(manifest),
        "oversized_upload_files": len(oversized),
        "pass": not missing_total and not oversized,
    }
    write_json(REPORTS_DIR / "validation_summary.json", result)
    return result


def write_schemas() -> None:
    ensure_dirs()
    common_string = {"type": "string"}
    common_number = {"type": ["number", "null"]}
    common_bool = {"type": "boolean"}
    write_json(
        SCHEMAS_DIR / "majors.schema.json",
        {
            "type": "object",
            "required": ["major_code", "major_name", "degree", "source_file", "needs_review"],
            "properties": {
                "major_code": common_string,
                "major_name": common_string,
                "major_category": common_string,
                "degree": common_string,
                "source_file": common_string,
                "needs_review": common_bool,
            },
        },
    )
    write_json(
        SCHEMAS_DIR / "graduation_requirements.schema.json",
        {
            "type": "object",
            "required": ["major_code", "major_name", "total_credits", "source_file", "needs_review"],
            "properties": {
                "major_code": common_string,
                "major_name": common_string,
                "total_credits": common_number,
                "theory_credits": common_number,
                "practice_credits": common_number,
                "general_required_credits": common_number,
                "general_elective_credits": common_number,
                "major_basic_credits": common_number,
                "major_required_credits": common_number,
                "major_limited_elective_credits": common_number,
                "major_optional_credits": common_number,
                "source_file": common_string,
                "needs_review": common_bool,
            },
        },
    )
    write_json(
        SCHEMAS_DIR / "courses.schema.json",
        {
            "type": "object",
            "required": ["course_code", "course_name", "major_code", "credits", "source_file", "needs_review"],
            "properties": {
                "course_code": common_string,
                "course_name": common_string,
                "major_code": common_string,
                "module": common_string,
                "course_type": common_string,
                "credits": common_number,
                "hours": common_number,
                "lecture_hours": common_number,
                "practice_hours": common_number,
                "semester": common_string,
                "assessment": common_string,
                "remark": common_string,
                "source_file": common_string,
                "needs_review": common_bool,
            },
        },
    )
    write_json(
        SCHEMAS_DIR / "practice_courses.schema.json",
        {
            "type": "object",
            "required": ["practice_code", "practice_name", "major_code", "credits", "source_file", "needs_review"],
            "properties": {
                "practice_code": common_string,
                "practice_name": common_string,
                "major_code": common_string,
                "module": common_string,
                "credits": common_number,
                "weeks": common_number,
                "semester": common_string,
                "organization": common_string,
                "source_file": common_string,
                "needs_review": common_bool,
            },
        },
    )


def write_run_metadata(summary: dict[str, Any]) -> None:
    sources = find_sources()
    metadata = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "source_root": str(SOURCE_ROOT),
        "source_files": [
            {
                "path": str(source.path.relative_to(PROJECT_ROOT)),
                "first_page": source.first_page,
                "mtime": datetime.fromtimestamp(source.path.stat().st_mtime).isoformat(timespec="seconds"),
                "sha256": file_sha256(source.path),
            }
            for source in sources
        ],
        "summary": summary,
    }
    write_json(REPORTS_DIR / "run_metadata.json", metadata)


def run_all() -> dict[str, Any]:
    ensure_dirs()
    write_schemas()
    inventory = build_inventory()
    merge_full_markdown()
    split_by_major()
    summary = build_major_outputs()
    summary["validation"] = validate_outputs()
    summary["source_count"] = inventory["source_count"]
    write_run_metadata(summary)
    return summary
