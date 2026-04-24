"""
Google Sheet 表頭解析最小回歸測試。
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from update_manifest import resolve_header_key


def run_header_resolution_smoke_test() -> None:
    cases = [
        ("細項分類明細", "細項分類明細"),
        ("氣候工項（預算型）明細", "氣候工項（預算型）明細"),
        ("非預算型效益明細", "非預算型效益明細"),
        ("細項分類明細（JSON）", "細項分類明細(JSON)"),
        ("氣候工項明細（JSON）", "氣候工項明細(JSON)"),
        ("非預算型效益與減量明細（JSON）", "非預算型效益明細(JSON)"),
    ]

    for source, expected in cases:
        resolved = resolve_header_key(source)
        assert resolved == expected, f"{source} 應解析為 {expected}，實際為 {resolved}"

    # JSON 欄不可誤配到非 JSON key
    json_resolved = resolve_header_key("氣候工項明細（JSON）")
    assert json_resolved is not None and "json" in json_resolved.lower(), (
        "JSON 欄位誤配到非 JSON key"
    )

    # 非 JSON 欄不可誤配到 JSON key
    non_json_resolved = resolve_header_key("氣候工項（預算型）明細")
    assert non_json_resolved is not None and "json" not in non_json_resolved.lower(), (
        "非 JSON 欄位誤配到 JSON key"
    )


if __name__ == "__main__":
    run_header_resolution_smoke_test()
    print("header resolution smoke test passed")
