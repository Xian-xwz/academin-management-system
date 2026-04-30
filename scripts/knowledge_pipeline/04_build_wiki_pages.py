from common import build_major_outputs


if __name__ == "__main__":
    summary = build_major_outputs()
    print(f"已生成 Wiki 页面，专业数量：{summary['majors']}")
