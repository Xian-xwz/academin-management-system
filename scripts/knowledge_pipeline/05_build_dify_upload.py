from common import build_dify_manifest, build_major_outputs, write_json, REPORTS_DIR


if __name__ == "__main__":
    build_major_outputs()
    manifest = build_dify_manifest()
    write_json(REPORTS_DIR / "dify_upload_manifest.json", manifest)
    print(f"已生成 Dify 上传文件清单：{len(manifest)} 个")
