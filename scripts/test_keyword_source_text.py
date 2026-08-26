"""Regression test for keyword source text assembly."""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from update_manifest import build_keyword_source_text, detect_keywords, split_keyword_matches


def run_keyword_source_text_smoke_test() -> None:
    source_text = build_keyword_source_text(
        "一般行政支援方案",
        "補充說明",
        ["彰化縣滯洪池新建工程", "縣道彰61線LED路燈汰換計畫"],
        "彰化縣淨零轉型宣導辦理活動",
    )
    assert "一般行政支援方案" in source_text
    assert "補充說明" in source_text
    assert "彰化縣淨零轉型宣導辦理活動" in source_text
    assert "彰化縣滯洪池新建工程" in source_text
    assert "縣道彰61線LED路燈汰換計畫" in source_text

    hit_ids = {hit.get("trigger_id") for hit in detect_keywords(source_text)}
    assert "KW_005" in hit_ids, "同計畫方案名稱中的滯洪池應納入關鍵字辨識"
    assert "KW_001" in hit_ids, "同計畫方案名稱中的 LED 應納入關鍵字辨識"
    assert "KW_026" in hit_ids, "正式標案名稱中的淨零應納入關鍵字辨識"

    # Production detection also scans adaptation_keyword_layers after the
    # primary dictionary, so exclusions must hold across both matching paths.
    excluded_temperature_cases = (
        "高溫殺菌設備採購",
        "極端高溫材料試驗設備採購",
        "極端低溫材料試驗設備採購",
    )
    for case_name in excluded_temperature_cases:
        matches = detect_keywords(case_name)
        strong_matches, concept_matches, _ = split_keyword_matches(matches)
        assert not strong_matches, f"{case_name} 不得由調適分層重新加入強提示"
        assert not concept_matches, f"{case_name} 不得命中溫度概念詞"

    outreach_matches = detect_keywords("辦理本縣遊民高低溫加強關懷措施")
    assert any(
        hit.get("trigger_id") == "KW_144" and hit.get("matched_term") == "高低溫"
        for hit in outreach_matches
    ), "高低溫遊民關懷措施應保留為調適概念提示"


if __name__ == "__main__":
    run_keyword_source_text_smoke_test()
    print("keyword source text smoke test passed")
