import json
from pathlib import Path

import streamlit as st
from packaging.requirements import InvalidRequirement
from packaging.requirements import Requirement

st.set_page_config(page_title="Climate Budget App Health Check", layout="wide")
st.title("彰化縣氣候預算系統｜啟動檢查頁")
st.caption("此版本先提供部署健檢，協助定位『Oh no. Error running app』原因。")


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
            # pip options (e.g. -r constraints.txt, --extra-index-url ...)
            continue
        try:
            Requirement(line)
        except InvalidRequirement as exc:
            return False, f"第 {idx} 行不是合法需求格式：{line}（{exc}）"

    return True, f"看起來是有效套件清單（共 {len(lines)} 行）"


repo = Path(__file__).resolve().parent
app_path = repo / "app.py"
config_path = repo / "config.json"
req_path = repo / "requirements.txt"

st.subheader("檔案狀態")
cols = st.columns(3)
for col, p in zip(cols, [app_path, config_path, req_path]):
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
if config_path.exists():
    raw = config_path.read_bytes()[:64]
    st.write("前 16 bytes:", " ".join(f"{b:02x}" for b in raw[:16]))
    if raw[:1] in (b"{", b"["):
        try:
            json.loads(config_path.read_text(encoding="utf-8"))
            st.success("config.json 可解析為 JSON")
        except Exception as exc:  # noqa: BLE001
            st.error(f"config.json 不是有效 JSON：{exc}")
    else:
        st.warning("config.json 不是 JSON 文字開頭，可能是錯置檔案（例如 pyc/binary）")
else:
    st.warning("config.json 不存在")

st.info("建議：先確保 app.py 是 Python 程式、requirements.txt 是 pip 套件清單，再重新部署。")
