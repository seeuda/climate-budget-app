"""
update_manifest.py
──────────────────
每次修改 keyword_dictionary.json 或 logic_mapping.json 後執行此腳本，
自動更新 config.json 的 manifest 區塊（checksums + checksum_updated_at）。

使用方式：
    python scripts/update_manifest.py

選用旗標：
    --kd-version 1.1.0    手動指定 keyword_dictionary 的新版本號
    --lm-version 1.1.0    手動指定 logic_mapping 的新版本號
    --note "說明文字"      附加到 change_log（可選）
    --dry-run             只顯示差異，不寫入

注意：
    每次修改對應 JSON 時，應同步遞增對應版本號（--kd-version / --lm-version），
    並在 change_log 說明變更內容。
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ_TAIPEI = timezone(timedelta(hours=8))
BASE_DIR   = Path(__file__).resolve().parent.parent   # 專案根目錄
CONFIG_PATH = BASE_DIR / "data" / "config.json"
KD_PATH     = BASE_DIR / "data" / "keyword_dictionary.json"
LM_PATH     = BASE_DIR / "data" / "logic_mapping.json"


def json_checksum(path: Path) -> str:
    """讀取 JSON、正規化（sort_keys + 無空白）後計算 MD5。"""
    with open(path, encoding="utf-8") as f:
        content = json.load(f)
    normalized = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def bump_patch(version: str) -> str:
    """1.0.0 → 1.0.1（只遞增 patch）。"""
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def main():
    parser = argparse.ArgumentParser(description="更新 config.json 的 manifest checksums")
    parser.add_argument("--kd-version", default=None, help="keyword_dictionary 新版本號（如 1.1.0）")
    parser.add_argument("--lm-version", default=None, help="logic_mapping 新版本號（如 1.1.0）")
    parser.add_argument("--note", default="", help="附加到 change_log 的說明（可選）")
    parser.add_argument("--dry-run", action="store_true", help="只顯示差異，不寫入")
    args = parser.parse_args()

    # 讀取現有 config
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)

    manifest = config.get("manifest", {})
    old_kd_checksum = manifest.get("checksums", {}).get("keyword_dictionary", "")
    old_lm_checksum = manifest.get("checksums", {}).get("logic_mapping", "")
    old_kd_ver      = manifest.get("keyword_dictionary_version", "1.0.0")
    old_lm_ver      = manifest.get("logic_mapping_version", "1.0.0")

    # 計算新 checksum
    new_kd_checksum = json_checksum(KD_PATH)
    new_lm_checksum = json_checksum(LM_PATH)

    kd_changed = (new_kd_checksum != old_kd_checksum)
    lm_changed = (new_lm_checksum != old_lm_checksum)

    # 決定新版本號
    if args.kd_version:
        new_kd_ver = args.kd_version
    elif kd_changed:
        new_kd_ver = bump_patch(old_kd_ver)
        print(f"[INFO] keyword_dictionary.json 已變更，版本自動遞增 {old_kd_ver} → {new_kd_ver}")
    else:
        new_kd_ver = old_kd_ver

    if args.lm_version:
        new_lm_ver = args.lm_version
    elif lm_changed:
        new_lm_ver = bump_patch(old_lm_ver)
        print(f"[INFO] logic_mapping.json 已變更，版本自動遞增 {old_lm_ver} → {new_lm_ver}")
    else:
        new_lm_ver = old_lm_ver

    # 顯示差異
    if not kd_changed and not lm_changed:
        print("[OK] 兩支 JSON 均未變更，manifest 無需更新。")
        sys.exit(0)

    print("\n變更摘要：")
    if kd_changed:
        print(f"  keyword_dictionary : checksum 已變更")
        print(f"    old: {old_kd_checksum}")
        print(f"    new: {new_kd_checksum}")
        print(f"  版本: {old_kd_ver} → {new_kd_ver}")
    if lm_changed:
        print(f"  logic_mapping      : checksum 已變更")
        print(f"    old: {old_lm_checksum}")
        print(f"    new: {new_lm_checksum}")
        print(f"  版本: {old_lm_ver} → {new_lm_ver}")

    if args.dry_run:
        print("\n[DRY-RUN] 未寫入，結束。")
        sys.exit(0)

    # 更新 manifest
    now_str = datetime.now(TZ_TAIPEI).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    manifest["keyword_dictionary_version"] = new_kd_ver
    manifest["logic_mapping_version"]      = new_lm_ver
    manifest["checksums"]["keyword_dictionary"] = new_kd_checksum
    manifest["checksums"]["logic_mapping"]      = new_lm_checksum
    manifest["checksum_updated_at"] = now_str
    manifest["last_synced_at"]      = now_str
    config["manifest"] = manifest

    # 補 change_log（若有 note）
    if args.note:
        schema = config.get("schema_version", {})
        log_entry = f"{now_str[:10]}: {args.note}"
        schema.setdefault("change_log", []).insert(0, log_entry)
        config["schema_version"] = schema

    # 寫回
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] manifest 已更新：{CONFIG_PATH}")
    print(f"  checksum_updated_at: {now_str}")


if __name__ == "__main__":
    main()
