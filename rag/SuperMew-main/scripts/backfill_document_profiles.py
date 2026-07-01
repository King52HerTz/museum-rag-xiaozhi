import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.env import load_env

load_env()

from backend.indexing.document_profile_store import DocumentProfileStore
from backend.indexing.milvus_client import get_milvus_store


SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".htm", ".html"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为已入库文档批量回填 document_profiles 业务画像")
    parser.add_argument("--museum", default="", help="统一回填的博物馆名称")
    parser.add_argument("--exhibition", default="", help="统一回填的展览名称")
    parser.add_argument("--exhibit-id", dest="exhibit_id", default="", help="统一回填的展品编号")
    parser.add_argument("--era", default="", help="统一回填的时代标签")
    parser.add_argument("--category", default="", help="统一回填的类别标签")
    parser.add_argument(
        "--overrides",
        default="",
        help="文件级覆盖 JSON 路径，支持为单个文件覆盖 exhibit_id/era/category 等字段",
    )
    parser.add_argument(
        "--source",
        choices=("uploaded", "indexed", "all"),
        default="all",
        help="从上传目录、Milvus 索引或两者合集收集文件名",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅打印将要回填的结果，不写入数据库")
    return parser.parse_args()


def normalize_text(value: str | None) -> str:
    return str(value or "").strip()


def detect_file_type(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").upper()


def load_override_payload(file_path: str) -> dict:
    if not file_path:
        return {"defaults": {}, "files": {}}
    raw = json.loads(Path(file_path).read_text(encoding="utf-8"))
    defaults = raw.get("defaults", {}) if isinstance(raw, dict) else {}
    files = raw.get("files", {}) if isinstance(raw, dict) else {}
    return {
        "defaults": defaults if isinstance(defaults, dict) else {},
        "files": files if isinstance(files, dict) else {},
    }


def collect_uploaded_filenames() -> list[str]:
    docs_dir = PROJECT_ROOT / "data" / "documents"
    if not docs_dir.exists():
        return []
    return sorted(
        {
            item.name
            for item in docs_dir.iterdir()
            if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES
        }
    )


def collect_indexed_filenames() -> list[str]:
    store = get_milvus_store()
    try:
        rows = store.query_all(output_fields=["filename"])
    except Exception:
        return []
    return sorted({str(row.get("filename") or "").strip() for row in rows if str(row.get("filename") or "").strip()})


def collect_target_filenames(source: str) -> list[str]:
    filenames: set[str] = set()
    if source in ("uploaded", "all"):
        filenames.update(collect_uploaded_filenames())
    if source in ("indexed", "all"):
        filenames.update(collect_indexed_filenames())
    return sorted(filenames)


def build_cli_defaults(args: argparse.Namespace) -> dict:
    return {
        "museum": normalize_text(args.museum),
        "exhibition": normalize_text(args.exhibition),
        "exhibit_id": normalize_text(args.exhibit_id),
        "era": normalize_text(args.era),
        "category": normalize_text(args.category),
    }


def merge_profile(filename: str, cli_defaults: dict, override_payload: dict) -> dict:
    override_defaults = override_payload.get("defaults", {})
    file_overrides = override_payload.get("files", {}).get(filename, {})

    profile = {
        "filename": filename,
        "file_type": detect_file_type(filename),
        "museum": "",
        "exhibition": "",
        "exhibit_id": "",
        "era": "",
        "category": "",
    }
    for payload in (cli_defaults, override_defaults, file_overrides):
        for key in ("museum", "exhibition", "exhibit_id", "era", "category"):
            value = normalize_text(payload.get(key) if isinstance(payload, dict) else "")
            if value:
                profile[key] = value
    return profile


def should_write_profile(profile: dict) -> bool:
    return any(profile.get(key) for key in ("museum", "exhibition", "exhibit_id", "era", "category"))


def main() -> int:
    args = parse_args()
    cli_defaults = build_cli_defaults(args)
    override_payload = load_override_payload(args.overrides)
    filenames = collect_target_filenames(args.source)

    if not filenames:
        print("[backfill] 未找到可回填的文档文件名。")
        return 1

    profiles = [merge_profile(name, cli_defaults, override_payload) for name in filenames]
    writable_profiles = [item for item in profiles if should_write_profile(item)]

    print(f"[backfill] source={args.source} | total_files={len(filenames)} | writable={len(writable_profiles)} | dry_run={args.dry_run}")
    for item in writable_profiles:
        print(
            "[backfill] {filename} | museum={museum} | exhibition={exhibition} | exhibit_id={exhibit_id} | era={era} | category={category}".format(
                **item
            )
        )

    skipped = [item["filename"] for item in profiles if not should_write_profile(item)]
    if skipped:
        print(f"[backfill] skipped_without_metadata={len(skipped)}")
        for name in skipped:
            print(f"[backfill] skipped: {name}")

    if args.dry_run:
        return 0

    store = DocumentProfileStore()
    for item in writable_profiles:
        store.upsert_profile(**item)

    print(f"[backfill] 已写入 document_profiles：{len(writable_profiles)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
