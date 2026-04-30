from common import build_major_outputs


if __name__ == "__main__":
    summary = build_major_outputs()
    print(
        "已抽取结构化数据："
        f"专业 {summary['majors']} 个，课程 {summary['courses']} 条，实践 {summary['practices']} 条"
    )
