from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WIKI_MAJORS_DIR = PROJECT_ROOT / "knowledge" / "wiki" / "majors"
DATA_MAJORS_PATH = PROJECT_ROOT / "data" / "majors.json"
DATA_GRADUATION_PATH = PROJECT_ROOT / "data" / "graduation_requirements.json"
DATA_COURSES_PATH = PROJECT_ROOT / "data" / "courses.json"
DATA_PRACTICES_PATH = PROJECT_ROOT / "data" / "practice_courses.json"
OUTPUT_DIR = PROJECT_ROOT / "knowledge" / "dify_upload_major"
REPORT_PATH = PROJECT_ROOT / "reports" / "dify_upload_major_result_selfhosted.json"
UPLOADER_PATH = PROJECT_ROOT / "scripts" / "dify_upload" / "upload_markdown_to_dify.py"

MODULE_FILES = [
    ("01_毕业要求与学分结构.md", "毕业要求与学分结构"),
    ("00_专业总览.md", "专业总览"),
    ("02_课程设置.md", "课程设置"),
    ("03_实践教学.md", "实践教学"),
    ("04_课程体系矩阵.md", "课程体系矩阵"),
]

ALIASES = {
    "电子科学与技术": ["电科", "电子科学", "电子科学专业"],
    "计算机科学与技术": ["计科", "计算机", "计算机专业"],
    "数据科学与大数据技术": ["大数据", "数科", "数据科学"],
    "电气工程及其自动化": ["电气", "电气自动化"],
    "机械设计制造及其自动化": ["机制", "机械设计制造"],
    "港口航道与海岸工程": ["港航", "港口航道"],
    "信息管理与信息系统": ["信管", "信息管理"],
    "国际经济与贸易": ["国贸"],
    "食品科学与工程": ["食品科学"],
    "食品质量与安全": ["食安"],
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_majors() -> list[dict[str, object]]:
    return json.loads(read_text(DATA_MAJORS_PATH))


def load_json_list(path: Path) -> list[dict[str, object]]:
    return json.loads(read_text(path))


def index_by_major_code(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    index: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        major_code = str(row.get("major_code") or "")
        index.setdefault(major_code, []).append(row)
    return index


def strip_context_header(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    skipping_meta = False
    for line in lines:
        if line.startswith("- 专业名称："):
            skipping_meta = True
            continue
        if skipping_meta and line.startswith("- "):
            continue
        skipping_meta = False
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def extract_credit_summary(credit_text: str) -> str:
    match = re.search(r"## 学分结构摘要\s*(.*?)(?=\n## |\Z)", credit_text, flags=re.S)
    if match:
        return match.group(1).strip()
    return "当前专业未识别到稳定的学分结构摘要，请结合下方课程结构比例表人工复核。"


def build_alias_lines(major_name: str) -> list[str]:
    aliases = ALIASES.get(major_name, [])
    if not aliases:
        return ["- 暂无常用简称，建议使用完整专业名称检索。"]
    return [f"- {alias}" for alias in aliases]


def fmt_credit(value: object) -> str:
    if value is None or value == "":
        return "待人工复核"
    return f"{value} 学分"


def clean_course_name(value: object) -> str:
    text = str(value or "").strip()
    for index, char in enumerate(text):
        if index > 0 and char.isascii() and char.isalpha():
            text = text[:index]
            break
    text = re.sub(r"\s+[A-Za-z][A-Za-z\s'’&().,-]+$", "", text).strip()
    return text or "未命名课程"


def unique_names(rows: list[dict[str, object]], key: str, limit: int = 12) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        name = clean_course_name(row.get(key))
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
        if len(names) >= limit:
            break
    return names


def format_name_list(names: list[str]) -> str:
    return "、".join(names) if names else "未在结构化数据中稳定识别，需结合下方课程清单核对。"


def build_graduation_condition_card(
    major: dict[str, object],
    graduation: dict[str, object] | None,
    courses: list[dict[str, object]],
    practices: list[dict[str, object]],
    credit_text: str,
) -> str:
    major_code = major.get("major_code") or "待人工复核"
    major_name = str(major["major_name"])
    professional_required = [
        row
        for row in courses
        if str(row.get("module") or "") in {"专业基础课", "专业课"} and "必修" in str(row.get("course_type") or "")
    ]
    if not professional_required:
        professional_required = [
            row
            for row in courses
            if str(row.get("module") or "") in {"专业基础课", "专业课"} or "必修" in str(row.get("course_type") or "")
        ]
    practice_names = unique_names(practices, "practice_name", limit=14)
    graduation_practices = [
        row
        for row in practices
        if "毕业" in str(row.get("practice_name") or "") or "毕业" in str(row.get("module") or "")
    ]

    if graduation:
        credit_lines = [
            f"- 毕业总学分：{fmt_credit(graduation.get('total_credits'))}",
            f"- 理论教学：{fmt_credit(graduation.get('theory_credits'))}",
            f"- 实践教学：{fmt_credit(graduation.get('practice_credits'))}",
            f"- 通识教育必修：{fmt_credit(graduation.get('general_required_credits'))}",
            f"- 通识教育选修：{fmt_credit(graduation.get('general_elective_credits'))}",
            f"- 专业基础课：{fmt_credit(graduation.get('major_basic_credits'))}",
            f"- 专业必修：{fmt_credit(graduation.get('major_required_credits'))}",
            f"- 专业限选：{fmt_credit(graduation.get('major_limited_elective_credits'))}",
            f"- 专业任选：{fmt_credit(graduation.get('major_optional_credits'))}",
        ]
    else:
        credit_lines = [extract_credit_summary(credit_text)]

    lines = [
        "## 毕业条件速查卡",
        "",
        "当用户询问“毕业条件”“毕业要求”“要修多少分”“学分够不够”“能不能毕业”时，优先引用本节；如果涉及个人是否达标，必须再结合学生已修课程、成绩、重修和毕业设计状态。",
        "",
        "### 1. 专业与版本",
        "",
        f"- 专业名称：{major_name}",
        f"- 专业代码：{major_code}",
        f"- 专业类：{major.get('major_category') or '待人工复核'}",
        f"- 授予学位：{major.get('degree') or '待人工复核'}",
        "- 培养方案来源：广东海洋大学2021版本科专业人才培养方案（上册）",
        "",
        "### 2. 学分结构要求",
        "",
        *credit_lines,
        "",
        "### 3. 必修与选修修读要求",
        "",
        "- 必须完成培养方案规定的通识必修、专业基础课、专业必修课和实践必修环节。",
        "- 选修类课程不能只看总学分，还要分别满足通识教育选修、专业限选、专业任选等模块最低学分。",
        f"- 专业核心/必修课程示例：{format_name_list(unique_names(professional_required, 'course_name', limit=14))}",
        "",
        "### 4. 实践教学与毕业环节要求",
        "",
        f"- 实践教学总要求：{fmt_credit(graduation.get('practice_credits')) if graduation else '见下方实践教学清单'}",
        f"- 实践环节示例：{format_name_list(practice_names)}",
        f"- 毕业实习/毕业设计相关环节：{format_name_list(unique_names(graduation_practices, 'practice_name', limit=8))}",
        "",
        "### 5. 毕业能力要求",
        "",
        "- 需达到培养方案规定的毕业能力要求，通常包括工程知识、问题分析、设计/开发解决方案、研究、现代工具使用、工程与社会、环境和可持续发展、职业规范、个人和团队、沟通、项目管理、终身学习等。",
        "- 课程体系矩阵用于说明课程如何支撑这些毕业能力要求；学生日常判断能否毕业时，优先核对课程、学分、实践和毕业设计/论文完成情况。",
        "",
        "### 6. 必须依赖个人学业数据判断的事项",
        "",
        "- 已修总学分是否达到本专业毕业总学分。",
        "- 所有必修课是否通过，是否存在挂科、重修或成绩异常。",
        "- 通识选修、专业限选、专业任选等模块是否分别达标。",
        "- 实践教学、实习实训、毕业实习和毕业设计/论文是否完成并通过。",
        "- 是否满足学校学位授予、处分、体测等校级规则；这些规则不完全来自本专业培养方案，需结合教务系统和学校制度。",
    ]
    return "\n".join(lines)


def build_major_document(
    major: dict[str, object],
    graduation_by_code: dict[str, dict[str, object]],
    courses_by_code: dict[str, list[dict[str, object]]],
    practices_by_code: dict[str, list[dict[str, object]]],
) -> str:
    major_name = str(major["major_name"])
    major_code = str(major.get("major_code") or "")
    major_dir = WIKI_MAJORS_DIR / major_name
    credit_text = read_text(major_dir / "01_毕业要求与学分结构.md")
    speed_card = build_graduation_condition_card(
        major,
        graduation_by_code.get(major_code),
        courses_by_code.get(major_code, []),
        practices_by_code.get(major_code, []),
        credit_text,
    )

    sections = [
        f"# {major_name}专业培养方案速查",
        "",
        "## 专业检索关键词",
        "",
        f"- 专业名称：{major_name}",
        f"- 专业代码：{major.get('major_code') or '待人工复核'}",
        f"- 专业类：{major.get('major_category') or '待人工复核'}",
        f"- 授予学位：{major.get('degree') or '待人工复核'}",
        "- 文档类型：分专业培养方案档案",
        "- 来源：广东海洋大学2021版本科专业人才培养方案（上册）",
        "",
        "## 常见简称",
        "",
        *build_alias_lines(major_name),
        "",
        speed_card,
        "",
        "## 专业完整知识页",
    ]

    for filename, title in MODULE_FILES:
        path = major_dir / filename
        if not path.exists():
            continue
        body = strip_context_header(read_text(path))
        sections.extend(["", f"## {title}", "", body])

    return "\n".join(sections).strip() + "\n"


def build_documents() -> None:
    majors = load_majors()
    graduation_rows = load_json_list(DATA_GRADUATION_PATH)
    graduation_by_code = {str(row.get("major_code") or ""): row for row in graduation_rows}
    courses_by_code = index_by_major_code(load_json_list(DATA_COURSES_PATH))
    practices_by_code = index_by_major_code(load_json_list(DATA_PRACTICES_PATH))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for major in majors:
        major_name = str(major["major_name"])
        if major_name.startswith("广东海洋大学"):
            continue
        write_text(OUTPUT_DIR / f"{major_name}.md", build_major_document(major, graduation_by_code, courses_by_code, practices_by_code))
        written += 1

    write_text(
        OUTPUT_DIR / "README.md",
        "\n".join(
            [
                "# dify_upload_major",
                "",
                "Dify 分专业知识库上传目录。",
                "",
                "生成规则：",
                "",
                "- 每个专业生成 1 个 Markdown 文档。",
                "- 文档开头固定包含“毕业条件速查卡”，覆盖总学分、模块学分、必修/选修、实践环节、毕业实习/设计和需个人数据判断的事项。",
                "- 后续依次拼接专业总览、课程设置、实践教学和课程体系矩阵，避免检索命中总览却漏掉学分结构。",
                "- 当前目录由 `scripts/dify_upload/build_and_upload_major_markdown.py` 生成。",
                "",
                f"当前生成专业文档数：{written}",
            ]
        )
        + "\n",
    )
    print(f"已生成分专业 Markdown：{written} 个，目录：{OUTPUT_DIR}", flush=True)


def upload_documents(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        "-u",
        str(UPLOADER_PATH),
        "--input-dir",
        str(OUTPUT_DIR),
        "--report",
        str(args.report),
        "--concurrency",
        str(args.concurrency),
        "--knowledge-requests-per-minute",
        str(args.knowledge_requests_per_minute),
        "--max-retries",
        str(args.max_retries),
        "--rate-limit-cooldown",
        str(args.rate_limit_cooldown),
        "--poll-interval",
        str(args.poll_interval),
        "--poll-timeout",
        str(args.poll_timeout),
    ]
    if args.force:
        command.append("--force")
    if args.limit is not None:
        command.extend(["--limit", str(args.limit)])

    print("开始上传分专业 Markdown 到 Dify 知识库。", flush=True)
    return subprocess.call(command, cwd=PROJECT_ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成并上传一个专业一个 Markdown 的 Dify 知识库文档")
    parser.add_argument("--build-only", action="store_true", help="只生成 Markdown，不上传")
    parser.add_argument("--upload-only", action="store_true", help="只上传，不重新生成 Markdown")
    parser.add_argument("--report", default=str(REPORT_PATH), help="上传报告路径")
    parser.add_argument("--limit", type=int, default=None, help="仅上传前 N 个专业文档，适合试跑")
    parser.add_argument("--force", action="store_true", help="重新上传报告中已有 success 的文档")
    parser.add_argument("--concurrency", type=int, default=1, help="上传并发数")
    parser.add_argument("--knowledge-requests-per-minute", type=int, default=10, help="Knowledge API 请求速率")
    parser.add_argument("--max-retries", type=int, default=5, help="单文档最大重试次数")
    parser.add_argument("--rate-limit-cooldown", type=int, default=120, help="限流后等待秒数")
    parser.add_argument("--poll-interval", type=int, default=10, help="索引状态轮询间隔秒数")
    parser.add_argument("--poll-timeout", type=int, default=900, help="单文档索引最大轮询秒数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.build_only and args.upload_only:
        raise SystemExit("--build-only 与 --upload-only 不能同时使用")
    if not args.upload_only:
        build_documents()
    if args.build_only:
        return
    raise SystemExit(upload_documents(args))


if __name__ == "__main__":
    main()
