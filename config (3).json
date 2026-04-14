"""Streamlit entrypoint for the climate budget self-assessment system.

Default behavior: launch the production self-assessment application from
`update_manifest.py`.
Optional behavior: open the startup diagnostic page via `?health_check=1`.
"""

from __future__ import annotations

import json
from pathlib import Path
import runpy

import streamlit as st
from packaging.requirements import InvalidRequirement, Requirement

REPO = Path(__file__).resolve().parent


def detect_file_type(path: Path) -> str:
    if not path.exists():
        return "missing"

    head = path.read_bytes()[:16]
    if head.startswith(b"{") or head.startswith(b"["):
        return "json_text"
    if head.startswith(b'"""'):
        return "python_text"
    if head[:4] == b"\xcb\r\r\n":
        return "python_pyc"
    return "unknown"


def inspect_app_py(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "`app.py` 不存在"

    src = path.read_text(encoding="utf-8", errors="ignore")

    try:
        compile(src, str(path), "exec")
        return True, "可通過 Python 語法編譯"
    except Exception as exc:  # noqa: BLE001
        return False, f"語法/編譯失敗：{exc}"


def inspect_requirements(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "`requirements.txt` 不存在"

    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()]
    lines = [line for line in lines if line and not line.startswith("#")]
    if not lines:
        return False, "`requirements.txt` 為空"

    for idx, line in enumerate(lines, start=1):
        if line.startswith(("-", "--")):
            continue
        try:
            Requirement(line)
        except InvalidRequirement as exc:
            return False, f"第 {idx} 行不是合法需求格式：{line}（{exc}）"

    return True, f"看起來是有效套件清單（共 {len(lines)} 行）"


def render_health_check() -> None:
    st.set_page_config(page_title="Climate Budget App Health Check", layout="wide")
    st.title("彰化縣氣候預算系統｜啟動檢查頁")
    st.caption("此版本先提供部署健檢，協助定位『Oh no. Error running app』原因。")

    app_path = REPO / "app.py"
    config_candidates = [REPO / "config.json", REPO / "data" / "config.json"]
    req_path = REPO / "requirements.txt"

    st.subheader("檔案狀態")
    cols = st.columns(3)
    for col, p in zip(cols, [app_path, config_candidates[0], req_path]):
        with col:
            st.markdown(f"**{p.name}**")
            st.code(detect_file_type(p))

    st.subheader("啟動關鍵檢查")
    app_ok, app_msg = inspect_app_py(app_path)
    req_ok, req_msg = inspect_requirements(req_path)

    if app_ok and req_ok:
        st.success("目前入口程式與依賴檔看起來可啟動。")
    else:
        st.error("偵測到可能導致『Error running app』的問題。")

    st.write("- app.py:", "✅" if app_ok else "❌", app_msg)
    st.write("- requirements.txt:", "✅" if req_ok else "❌", req_msg)

    st.subheader("config.json 檢查")
    selected_config = None
    parse_errors: dict[Path, Exception] = {}
    for candidate in config_candidates:
        if not candidate.exists():
            continue
        raw = candidate.read_bytes()[:64]
        if raw[:1] not in (b"{", b"["):
            continue
        try:
            json.loads(candidate.read_text(encoding="utf-8"))
            selected_config = candidate
            break
        except Exception as exc:  # noqa: BLE001
            parse_errors[candidate] = exc
            continue

    if selected_config is not None:
        st.success(f"使用設定檔：{selected_config.relative_to(REPO)}（可解析為 JSON）")
        raw = selected_config.read_bytes()[:64]
        st.write("前 16 bytes:", " ".join(f"{b:02x}" for b in raw[:16]))
        if selected_config != config_candidates[0] and config_candidates[0].exists():
            if config_candidates[0] in parse_errors:
                st.warning(f"根目錄 config.json JSON 解析失敗，已改用 data/config.json：{parse_errors[config_candidates[0]]}")
            else:
                st.warning("根目錄 config.json 非有效 JSON，已改用 data/config.json。")
    else:
        primary = config_candidates[0]
        fallback = config_candidates[1]
        if primary.exists():
            raw = primary.read_bytes()[:64]
            st.write("根目錄 config.json 前 16 bytes:", " ".join(f"{b:02x}" for b in raw[:16]))
            if raw[:1] in (b"{", b"[") and primary in parse_errors:
                st.error(f"config.json 是 JSON 文字開頭，但解析失敗：{parse_errors[primary]}")
            else:
                st.warning("config.json 不是 JSON 文字開頭，可能是錯置檔案（例如 pyc/binary）")
        if fallback.exists() and fallback in parse_errors:
            st.error(f"data/config.json 存在但不可解析，請檢查 JSON 格式：{parse_errors[fallback]}")
        else:
            st.warning("找不到可用的 config.json（已檢查根目錄與 data/config.json）。")

    st.info("建議：先確保 app.py 是 Python 程式、requirements.txt 是 pip 套件清單，再重新部署。")


def render_health_check_link() -> None:
    st.markdown(
        """
        <style>
        .health-check-link {
            position: fixed;
            right: 16px;
            bottom: 16px;
            z-index: 9999;
            background: #113f2d;
            color: #fff !important;
            padding: 8px 12px;
            border-radius: 999px;
            font-size: 13px;
            text-decoration: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .health-check-link:hover { background: #0d2f21; }
        </style>
        <a class="health-check-link" href="?health_check=1" target="_self">🩺 啟動檢查頁</a>
        """,
        unsafe_allow_html=True,
    )


if str(st.query_params.get("health_check", "")).lower() in {"1", "true", "yes", "on"}:
    render_health_check()
else:
    runpy.run_path(str(REPO / "update_manifest.py"), run_name="__main__")
    render_health_check_link()
