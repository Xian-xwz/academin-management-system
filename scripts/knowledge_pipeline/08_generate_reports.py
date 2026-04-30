import json

from common import REPORTS_DIR, build_reports, read_text


if __name__ == "__main__":
    field_path = REPORTS_DIR / "field_validation_report.json"
    field_report = json.loads(read_text(field_path)) if field_path.exists() else []
    build_reports(field_report)
    print("已重新生成报告")
