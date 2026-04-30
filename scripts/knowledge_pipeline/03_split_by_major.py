from common import split_by_major


if __name__ == "__main__":
    majors = split_by_major()
    print(f"已切分专业数量：{len(majors)}")
