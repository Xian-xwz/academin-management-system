from common import build_inventory


if __name__ == "__main__":
    result = build_inventory()
    print(f"已扫描来源文件：{result['source_count']} 个")
