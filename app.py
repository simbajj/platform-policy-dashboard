from __future__ import annotations

import os
import re
from html import escape
from datetime import date, datetime, timedelta, timezone
from typing import Any

import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ALLOWED_EMAIL_DOMAIN = "neowiz.com"


def get_logged_in_email():
    user = getattr(st, "user", None)
    if not user:
        return ""
    if hasattr(user, "get"):
        return user.get("email", "") or ""
    return getattr(user, "email", "") or ""


def require_neowiz_login():
    if not hasattr(st, "login") or not hasattr(st, "user"):
        st.error("현재 Streamlit 버전에서 로그인 기능을 사용할 수 없습니다. requirements.txt 설치 상태를 확인해주세요.")
        st.stop()

    if not bool(getattr(st.user, "is_logged_in", False)):
        st.markdown("## 플랫폼 정책 대응 현황")
        st.caption("NEOWIZ 계정으로 로그인하면 대시보드를 볼 수 있습니다.")
        if st.button("Google 계정으로 로그인", type="primary"):
            st.login()
        st.stop()

    email = get_logged_in_email()
    if not email.lower().endswith("@" + ALLOWED_EMAIL_DOMAIN):
        st.error("접근 권한이 없습니다. neowiz.com 계정으로 로그인해주세요.")
        st.caption(f"현재 로그인 계정: {email or '-'}")
        if st.button("로그아웃"):
            st.logout()
        st.stop()

    with st.sidebar:
        st.success(f"로그인: {email}")
        if st.button("로그아웃", use_container_width=True):
            st.logout()


def reset_response_filters(min_date, max_date):
        st.session_state["_reset_response_filters_requested"] = True
        st.session_state["_reset_response_filters_requested"] = True
        st.session_state["_reset_response_filters_requested"] = True
        st.session_state["_reset_response_filters_requested"] = True
        st.session_state["_reset_response_filters_requested"] = True
        st.session_state["_reset_response_filters_requested"] = True
        st.session_state["_reset_response_filters_requested"] = True
        st.session_state["_reset_response_filters_requested"] = True
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials


SHEET_NAME = "시트1"
SPREADSHEET_ID = "1jhgiYT2qlHG5iLdCEBxXun0Flv0ucZ5cYofQarOFCNs"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

RAW_COLUMNS = [
    "날짜",
    "플랫폼",
    "제목",
    "심각도",
    "데드라인",
    "대응상태",
    "담당자",
    "메모",
    "Gmail링크",
    "신규",
    "최종수정",
]

COLMAP = {
    "날짜": "date",
    "플랫폼": "platform",
    "제목": "title",
    "심각도": "severity",
    "데드라인": "deadline",
    "대응상태": "status",
    "담당자": "assignee",
    "메모": "memo",
    "Gmail링크": "gmailLink",
    "신규": "isNew",
    "최종수정": "lastModified",
}

STATUS_VALUES = ["❌ 미대응", "📋 검토 전", "🔄 진행 중", "✅ 완료"]
SEVERITY_VALUES = ["긴급", "주의", "참고"]
PLATFORM_VALUES = ["구글", "애플", "Firebase", "기타"]
STATUS_MAP = {"📋 검토중": "📋 검토 전", "🔄 진행중": "🔄 진행 중"}
SEVERITY_ORDER = {"긴급": 0, "주의": 1, "참고": 2}
STATUS_ORDER = {"❌ 미대응": 0, "📋 검토 전": 1, "🔄 진행 중": 2, "✅ 완료": 3}
KST = timezone(timedelta(hours=9))


st.set_page_config(
    page_title="플랫폼 정책 대응 현황",
    page_icon="🛡️",
    layout="wide",
)


def inject_style() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        section[data-testid="stSidebar"] {
            background: #f1f4f8;
            border-right: 1px solid #d8dee8;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1.4rem;
        }
        .block-container {
            padding-top: 2.6rem;
        }
        div[data-testid="stHorizontalBlock"]:has(button[aria-label="↻ 새로고침"]) {
            padding-top: 0.35rem;
            overflow: visible;
        }
        div[data-testid="stButton"] > button[kind="primary"] {
            background: #4f6ef7 !important;
            color: #fff !important;
            border: 1px solid #4f6ef7 !important;
            font-weight: 800 !important;
            box-shadow: 0 4px 12px rgba(79,110,247,0.20);
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: #3a5be0 !important;
            border-color: #3a5be0 !important;
            color: #fff !important;
        }
        div[data-testid="stMetric"] {
            background: #fff;
            border: 1px solid #e8eaf0;
            border-radius: 10px;
            padding: 12px 14px;
        }
        .section {
            background: #fff;
            border: 1px solid #e8eaf0;
            border-radius: 10px;
            padding: 18px 20px;
            margin: 0 0 16px 0;
        }
        .section-title {
            font-size: 16px;
            font-weight: 800;
            color: #1a202c;
            margin-bottom: 12px;
        }
        .card {
            background: #fff;
            border: 1px solid #e8eaf0;
            border-left: 4px solid #38a169;
            border-radius: 10px;
            padding: 14px 16px;
            margin-bottom: 10px;
        }
        .card.urgent { border-left-color: #e53e3e; background: #fffafa; }
        .card.warning { border-left-color: #dd6b20; background: #fffdf7; }
        .muted { color: #718096; font-size: 12px; }
        .title { font-weight: 750; color: #1a202c; line-height: 1.45; }
        .badge {
            display: inline-block;
            font-size: 12px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 7px;
            margin-right: 4px;
            white-space: nowrap;
        }
        .pb-google { background:#e8f5e9; color:#2e7d32; }
        .pb-apple { background:#f0f0ff; color:#6b46c1; }
        .pb-firebase { background:#fff8e1; color:#f57f17; }
        .pb-default { background:#f1f3f4; color:#718096; }
        .sev-urgent { background:#fff5f5; color:#c53030; }
        .sev-warning { background:#fffaf0; color:#c05621; }
        .sev-info { background:#f0fff4; color:#276749; }
        .st-done { background:#f0fff4; color:#276749; }
        .st-progress { background:#ebf8ff; color:#2b6cb0; }
        .st-review { background:#f1f3f4; color:#718096; }
        .st-pending { background:#fff5f5; color:#c53030; }
        .dday-red { background:#fff5f5; color:#c53030; }
        .dday-orange { background:#fff8ec; color:#c05621; }
        .dday-gray { background:#f1f3f4; color:#718096; }
        .needs-update {
            background:#fff5f5;
            color:#c53030;
            border:1px solid #fed7d7;
            font-weight:900;
        }
        .card-link-wrap {
            display: block;
            text-decoration: none !important;
            color: inherit !important;
            margin-bottom: 10px;
        }
        .card-link-wrap:hover .card {
            border-color: #c5cef9;
            box-shadow: 0 4px 16px rgba(79,110,247,.10);
            transform: translateY(-1px);
        }
        .drawer-panel {
            background: #fff;
            border-left: 1px solid #e8eaf0;
            padding: 4px 4px 16px 18px;
            position: sticky;
            top: 12px;
        }
        .drawer-title {
            font-size: 16px;
            font-weight: 800;
            line-height: 1.45;
            color: #1a202c;
            margin-bottom: 14px;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            border-bottom: 1px solid #edf0f5;
            padding: 7px 0;
            font-size: 13px;
        }
        .detail-key { color: #a0aec0; flex-shrink: 0; }
        .detail-val { color: #1a202c; font-weight: 650; text-align: right; }
        div[data-testid="stButton"] > button { border-radius: 10px; }
        .list-hint {
            color: #718096;
            font-size: 12px;
            margin-bottom: 8px;
        }
        .card-title-divider {
            border: 0;
            border-top: 1px solid #e8eaf0;
            margin: 6px 0 6px 0;
        }
        .card-soft-divider {
            border: 0;
            border-top: 1px dashed #e2e8f0;
            margin: 7px 0;
        }
        .policy-summary-card {
            border-left: 4px solid #a0aec0;
            border-radius: 8px;
            padding: 10px 12px 4px 12px;
            margin: 0;
        }
        .policy-summary-card.status-done {
            background: #f0fff4;
            border-left-color: #38a169;
        }
        .policy-summary-card.status-progress {
            background: #ebf8ff;
            border-left-color: #3182ce;
        }
        .policy-summary-card.status-review {
            background: #f8f9fb;
            border-left-color: #a0aec0;
        }
        .policy-summary-card.status-pending {
            background: #fff5f5;
            border-left-color: #e53e3e;
        }
        div[data-testid="stHorizontalBlock"]:has(.policy-summary-card.status-done) {
            background: #f0fff4;
            border-left: 4px solid #38a169;
            border-radius: 10px;
            border: 1px solid #c6f6d5;
            border-left-width: 4px;
            padding: 10px 12px 22px 12px;
            margin: 0 0 12px 0;
            overflow: visible;
            transition: transform .16s ease, box-shadow .18s ease, border-color .18s ease;
        }
        div[data-testid="stHorizontalBlock"]:has(.policy-summary-card.status-progress) {
            background: #ebf8ff;
            border-left: 4px solid #3182ce;
            border-radius: 10px;
            border: 1px solid #bee3f8;
            border-left-width: 4px;
            padding: 10px 12px 22px 12px;
            margin: 0 0 12px 0;
            overflow: visible;
            transition: transform .16s ease, box-shadow .18s ease, border-color .18s ease;
        }
        div[data-testid="stHorizontalBlock"]:has(.policy-summary-card.status-review) {
            background: #f8f9fb;
            border-left: 4px solid #a0aec0;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            border-left-width: 4px;
            padding: 10px 12px 22px 12px;
            margin: 0 0 12px 0;
            overflow: visible;
            transition: transform .16s ease, box-shadow .18s ease, border-color .18s ease;
        }
        div[data-testid="stHorizontalBlock"]:has(.policy-summary-card.status-pending) {
            background: #fff5f5;
            border-left: 4px solid #e53e3e;
            border-radius: 10px;
            border: 1px solid #fed7d7;
            border-left-width: 4px;
            padding: 10px 12px 22px 12px;
            margin: 0 0 12px 0;
            overflow: visible;
            transition: transform .16s ease, box-shadow .18s ease, border-color .18s ease;
        }
        div[data-testid="stHorizontalBlock"]:has(.policy-summary-card):hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 22px rgba(26, 32, 44, 0.10);
        }
        div[data-testid="stHorizontalBlock"]:has(.policy-summary-card.jump-highlight) {
            animation: jumpHighlight 3.2s ease forwards;
            border-color: #facc15 !important;
            box-shadow: 0 0 0 3px rgba(250, 204, 21, 0.38), 0 10px 26px rgba(26, 32, 44, 0.12);
        }
        .policy-summary-card.jump-highlight::before {
            content: "선택된 항목";
            display: inline-block;
            margin-bottom: 6px;
            background: #facc15;
            color: #713f12;
            font-size: 11px;
            font-weight: 900;
            padding: 2px 8px;
            border-radius: 999px;
        }
        @keyframes jumpHighlight {
            0%, 100% { transform: translateY(0); }
            18% { transform: translateY(-3px); }
            36% { transform: translateY(0); }
        }
        div[data-testid="stHorizontalBlock"]:has(.policy-summary-card) .policy-summary-card {
            background: transparent;
            border: 0;
            padding: 0;
        }
        div[data-testid="stHorizontalBlock"]:has(.policy-summary-card) div[data-testid="stToggle"] {
            display: flex;
            justify-content: flex-end;
            padding-top: 2px;
        }
        .policy-card-title {
            font-weight: 800;
            color: #1a202c;
            line-height: 1.35;
            margin-bottom: 6px;
        }
        .policy-card-tags {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 4px;
            margin-bottom: 7px;
        }
        .policy-card-meta {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 8px;
            border-top: 1px solid rgba(0,0,0,0.08);
            padding-top: 8px;
            padding-bottom: 8px;
        }
        .policy-toggle-wrap {
            padding-top: 4px;
            display: flex;
            justify-content: flex-end;
        }
        .policy-card-meta-item {
            min-width: 0;
        }
        .policy-card-meta-label {
            display: block;
            color: #718096;
            font-size: 11px;
            font-weight: 650;
            margin-bottom: 2px;
        }
        .policy-card-meta-value {
            display: block;
            color: #1a202c;
            font-size: 13px;
            font-weight: 700;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .overview-card-link {
            display: block;
            text-decoration: none !important;
            color: inherit !important;
        }
        .overview-card-link:hover .policy-summary-card {
            transform: translateY(-2px);
            box-shadow: 0 8px 22px rgba(26, 32, 44, 0.10);
        }
        .urgent-line {
            display: flex;
            align-items: center;
            gap: 8px;
            min-height: 38px;
            border: 1px solid #d8dee8;
            border-radius: 8px;
            padding: 7px 12px;
            margin-bottom: 8px;
            background: #fff;
            color: #1a202c;
            text-decoration: none !important;
            transition: transform .14s ease, box-shadow .16s ease, border-color .16s ease;
        }
        .urgent-line:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 14px rgba(26, 32, 44, 0.08);
            border-color: #c5cef9;
        }
        .urgent-line-title {
            font-weight: 800;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .urgent-line-meta {
            color: #718096;
            font-size: 12px;
            white-space: nowrap;
            margin-left: auto;
        }
        .status-tabs-spacer {
            height: 12px;
        }
        .success-toast {
            position: fixed;
            top: 72px;
            right: 28px;
            z-index: 9999;
            background: #22c55e;
            border: 1px solid #16a34a;
            color: #fff;
            border-radius: 12px;
            padding: 13px 18px;
            font-weight: 900;
            box-shadow: 0 10px 24px rgba(34, 197, 94, 0.28);
            animation: toastInOut 3.2s ease forwards;
            pointer-events: none;
        }
        @keyframes toastInOut {
            0% { opacity: 0; transform: translateY(-8px) translateX(8px); }
            12% { opacity: 1; transform: translateY(0) translateX(0); }
            78% { opacity: 1; transform: translateY(0) translateX(0); }
            100% { opacity: 0; transform: translateY(-8px) translateX(8px); }
        }
        div[data-testid="stVerticalBlock"]:has(.card-title-divider) {
            gap: 0.35rem;
        }
        .card-link-wrap .card,
        .card-link-wrap .title,
        .card-link-wrap .muted,
        .card-link-wrap .card-line {
            display: block;
        }
        .card-link-wrap .card {
            cursor: pointer;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_credentials() -> Credentials:
    try:
        service_account = st.secrets.get("gcp_service_account")
    except Exception:
        service_account = None

    if service_account:
        return Credentials.from_service_account_info(
            dict(service_account),
            scopes=SCOPES,
        )

    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        return Credentials.from_service_account_file(credentials_path, scopes=SCOPES)

    st.error("Google 서비스 계정 인증 정보가 없습니다. `.streamlit/secrets.toml`을 설정해주세요.")
    st.stop()


@st.cache_resource(show_spinner=False)
def get_sheet() -> gspread.Worksheet:
    credentials = get_credentials()
    client = gspread.authorize(credentials)
    try:
        return client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    except PermissionError:
        st.error("Google Sheet 접근 권한이 없습니다.")
        st.write("앱이 접근하려는 시트 ID:", SPREADSHEET_ID)
        st.write("앱이 사용 중인 서비스 계정:", getattr(credentials, "service_account_email", "확인 불가"))
        st.info("위 서비스 계정이 해당 Google Sheet에 편집자로 공유되어 있는지 확인해주세요.")
        st.stop()


def format_ymd(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if not text or text == "-":
        return "-"

    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return text
    return parsed.strftime("%Y-%m-%d")


def normalize_platform(value: Any) -> str:
    text = str(value or "").strip()
    mapping = {
        "Apple": "애플",
        "Google": "구글",
        "Google Play": "구글",
        "AdMob": "구글",
        "Google Cloud": "구글",
        "Google Payments": "구글",
    }
    return mapping.get(text, text if text in PLATFORM_VALUES else "기타")


def normalize_status(value: Any) -> str:
    text = str(value or "").strip()
    return STATUS_MAP.get(text, text or "📋 검토 전")


@st.cache_data(ttl=60, show_spinner="구글 시트에서 데이터를 읽고 있습니다...")
def load_data() -> pd.DataFrame:
    rows = get_sheet().get_all_values()
    if len(rows) <= 1:
        return pd.DataFrame(columns=list(COLMAP.values()))

    body = rows[1:]
    normalized_rows = []
    for row in body:
        padded = (row + [""] * len(RAW_COLUMNS))[: len(RAW_COLUMNS)]
        normalized_rows.append(dict(zip(RAW_COLUMNS, padded)))

    df = pd.DataFrame(normalized_rows).rename(columns=COLMAP)
    for col in COLMAP.values():
        if col not in df.columns:
            df[col] = ""

    df["date"] = df["date"].map(format_ymd)
    df["deadline"] = df["deadline"].map(lambda v: format_ymd(v) if str(v or "").strip() else "-")
    df["platform"] = df["platform"].map(normalize_platform)
    df["status"] = df["status"].map(normalize_status)
    df["severity"] = df["severity"].replace("", "참고")
    df["row_number"] = df.index + 2
    return dedupe_rows(df)


def dedupe_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    selected = []
    for _, group in df.groupby(df["title"].fillna("").str.strip(), sort=False):
        non_done = group[~group["status"].str.contains("완료", na=False)]
        if not non_done.empty:
            selected.append(non_done)
        else:
            selected.append(group.sort_values("date", ascending=False).head(1))
    return pd.concat(selected, ignore_index=True)


def is_new(date_text: str) -> bool:
    parsed = pd.to_datetime(date_text, errors="coerce")
    if pd.isna(parsed):
        return False
    diff = (datetime.now(KST).date() - parsed.date()).days
    return 0 <= diff <= 2


def calc_dday(deadline: str) -> int | None:
    if not deadline or deadline == "-":
        return None
    parsed = pd.to_datetime(deadline, errors="coerce")
    if pd.isna(parsed):
        return None
    return (parsed.date() - datetime.now(KST).date()).days


def parse_date_input(value: Any) -> date | None:
    if not value or str(value).strip() == "-":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def dday_text(deadline: str) -> str:
    dd = calc_dday(deadline)
    if dd is None:
        return ""
    if dd < 0:
        return f"D+{abs(dd)}"
    if dd == 0:
        return "D-Day"
    return f"D-{dd}"


def is_deadline_missing(deadline: Any) -> bool:
    return not deadline or str(deadline).strip() in {"", "-"}


def needs_status_update(row: pd.Series) -> bool:
    if "완료" in str(row.get("status", "")):
        return False
    if not is_deadline_missing(row.get("deadline")):
        return False
    parsed = pd.to_datetime(row.get("date"), errors="coerce")
    if pd.isna(parsed):
        return False
    return (datetime.now(KST).date() - parsed.date()).days > 3


def needs_update_badge(row: pd.Series) -> str:
    if not needs_status_update(row):
        return ""
    return '<span class="badge needs-update">상태 업데이트 필요</span>'


def html_badge(text: str, klass: str) -> str:
    return f'<span class="badge {klass}">{text}</span>'


def platform_badge(platform: str) -> str:
    klass = {
        "구글": "pb-google",
        "애플": "pb-apple",
        "Firebase": "pb-firebase",
    }.get(platform, "pb-default")
    return html_badge(platform or "기타", klass)


def severity_badge(severity: str) -> str:
    klass = {"긴급": "sev-urgent", "주의": "sev-warning", "참고": "sev-info"}.get(severity, "sev-info")
    prefix = {"긴급": "🔴", "주의": "🟠", "참고": "🟢"}.get(severity, "")
    return html_badge(f"{prefix} {severity or '-'}", klass)


def status_badge(status: str) -> str:
    klass = (
        "st-done"
        if "완료" in status
        else "st-progress"
        if "진행" in status
        else "st-pending"
        if "미대응" in status
        else "st-review"
    )
    return html_badge(status or "-", klass)


def dday_badge(deadline: str) -> str:
    dd = calc_dday(deadline)
    if dd is None:
        return ""
    klass = "dday-gray" if dd < 0 else "dday-red" if dd <= 7 else "dday-orange" if dd <= 30 else "dday-gray"
    return html_badge(dday_text(deadline), klass)


def gmail_search_url(title: str) -> str:
    if not title:
        return ""
    from urllib.parse import quote

    return "https://mail.google.com/mail/u/0/#search/" + quote(f"subject:({title})")


def update_row(row_number: int, payload: dict[str, str], opened_last_modified: str) -> tuple[bool, str]:
    sheet = get_sheet()
    current_last_modified = str(sheet.cell(row_number, 11).value or "")
    if opened_last_modified and current_last_modified != opened_last_modified:
        return False, "conflict"

    now = datetime.now(timezone.utc).isoformat()
    values = [[
        payload["severity"],
        payload["deadline"] or "-",
        payload["status"],
        payload["assignee"],
        payload["memo"],
        now,
    ]]
    sheet.update([values[0][:5]], f"D{row_number}:H{row_number}")
    sheet.update([[now]], f"K{row_number}:K{row_number}")
    load_data.clear()
    return True, now


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    stat_filter = st.session_state.get("stat_filter", "전체")
    platform = st.session_state.get("platform_filter", "전체")
    status = st.session_state.get("status_filter", "전체")
    response_status_tab = st.session_state.get("response_status_tab", "전체")
    query = st.session_state.get("search_query", "").strip().lower()
    date_range = st.session_state.get("date_filter")

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        parsed_dates = pd.to_datetime(out["date"], errors="coerce").dt.date
        out = out[(parsed_dates >= start_date) & (parsed_dates <= end_date)]

    if stat_filter != "전체":
        if stat_filter == "미대응":
            out = out[out["status"].str.contains("미대응", na=False)]
        else:
            out = out[out["severity"] == stat_filter]
    if platform != "전체":
        out = out[out["platform"] == platform]
    if status != "전체":
        out = out[out["status"].str.contains(status.replace(" 중", ""), na=False)]
    if response_status_tab != "전체":
        out = out[out["status"].str.contains(response_status_tab.replace(" 중", ""), na=False)]
    if query:
        haystack = (
            out["title"].fillna("")
            + " "
            + out["platform"].fillna("")
            + " "
            + out["assignee"].fillna("")
        ).str.lower()
        out = out[haystack.str.contains(re.escape(query), na=False)]

    sort_option = st.session_state.get("sort_option", "날짜 최신순")
    if sort_option == "날짜 최신순":
        out = out.assign(_sort=pd.to_datetime(out["date"], errors="coerce")).sort_values("_sort", ascending=False)
    elif sort_option == "날짜 오래된순":
        out = out.assign(_sort=pd.to_datetime(out["date"], errors="coerce")).sort_values("_sort", ascending=True)
    elif sort_option == "심각도 높은순":
        out = out.assign(_sort=out["severity"].map(SEVERITY_ORDER).fillna(9)).sort_values("_sort")
    elif sort_option == "데드라인 임박순":
        out = out.assign(_sort=pd.to_datetime(out["deadline"].replace("-", pd.NA), errors="coerce")).sort_values("_sort")

    if response_status_tab == "전체" and not out.empty:
        out = out.assign(_needs_update=out.apply(needs_status_update, axis=1))
        out = out.sort_values("_needs_update", ascending=False, kind="stable")
    return out.drop(columns=[c for c in ["_sort", "_needs_update"] if c in out.columns])


def render_header(df: pd.DataFrame) -> None:
    left, right = st.columns([0.72, 0.28])
    with left:
        st.title("🛡️ 플랫폼 정책 대응 현황")
        new_count = int(df["date"].map(is_new).sum()) if not df.empty else 0
        st.caption(
            f"마지막 업데이트: {datetime.now(KST).strftime('%Y-%m-%d %H:%M')} KST · "
            f"총 {len(df)}건" + (f" · 신규 {new_count}건" if new_count else "")
        )
    with right:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("↻ 새로고침", use_container_width=True, type="primary"):
            load_data.clear()
            st.rerun()


def render_overview(df: pd.DataFrame) -> None:
    urgent_items = df[
        (~df["status"].str.contains("완료", na=False))
        & (
            (df["severity"] == "긴급")
            | df["deadline"].map(lambda x: (calc_dday(x) is not None) and 0 <= calc_dday(x) <= 3)
        )
    ].copy()
    urgent_items["_dday"] = urgent_items["deadline"].map(lambda x: calc_dday(x) if calc_dday(x) is not None else 999)
    urgent_items = urgent_items.sort_values("_dday")

    st.markdown('<div class="section-title">🚨 즉시 대응 필요</div>', unsafe_allow_html=True)
    if urgent_items.empty:
        st.success("즉시 대응이 필요한 항목이 없습니다.")
    else:
        for _, row in urgent_items.head(6).iterrows():
            render_overview_urgent_line(row)

    st.markdown('<hr class="card-title-divider">', unsafe_allow_html=True)
    st.markdown("### 데드라인 리스크")
    render_deadline_risk_table(df)

    st.markdown('<hr class="card-title-divider">', unsafe_allow_html=True)
    st.markdown("### 플랫폼별 현황")
    left, right = st.columns([0.62, 0.38])
    platform_counts = df["platform"].value_counts().reindex(PLATFORM_VALUES, fill_value=0).reset_index()
    platform_counts.columns = ["플랫폼", "건수"]
    with left:
        fig = px.bar(platform_counts, x="건수", y="플랫폼", orientation="h", text="건수")
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        status_counts = pd.DataFrame(
            {
                "상태": ["완료", "진행 중", "검토 전", "미대응"],
                "건수": [
                    df["status"].str.contains("완료", na=False).sum(),
                    df["status"].str.contains("진행", na=False).sum(),
                    df["status"].str.contains("검토", na=False).sum(),
                    df["status"].str.contains("미대응", na=False).sum(),
                ],
            }
        )
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=status_counts["상태"],
                    values=status_counts["건수"],
                    hole=0.68,
                    marker_colors=["#38a169", "#3182ce", "#a0aec0", "#e53e3e"],
                    domain={"x": [0.08, 0.82], "y": [0.08, 0.92]},
                )
            ]
        )
        fig.update_layout(height=230, margin=dict(l=18, r=42, t=24, b=18), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<hr class="card-title-divider">', unsafe_allow_html=True)
    st.markdown("### 플랫폼 × 심각도 매트릭스")
    render_platform_severity_matrix(df)

    st.markdown('<hr class="card-title-divider">', unsafe_allow_html=True)
    st.markdown("### 일별 접수 · 처리 추이")
    days = st.radio(
        "기간",
        [7, 14, 30],
        index=0,
        horizontal=True,
        format_func=lambda x: f"{x}일",
        label_visibility="collapsed",
    )
    render_daily_chart(df, int(days))

    st.markdown('<hr class="card-title-divider">', unsafe_allow_html=True)
    st.markdown("### 최근 활동 & 미처리 알림")
    recent_col, pending_col = st.columns(2)
    with recent_col:
        st.markdown("**최근 신규 접수**")
        recent = df[df["date"].map(is_new)].sort_values("date", ascending=False).head(5)
        render_small_list(recent, clickable=True)
    with pending_col:
        st.markdown("**미처리 항목**")
        pending = df[
            df["status"].str.contains("미대응", na=False)
            | (
                df["deadline"].map(lambda x: (calc_dday(x) is not None) and calc_dday(x) < 0)
                & ~df["status"].str.contains("완료", na=False)
            )
        ].head(5)
        render_small_list(pending, clickable=True)

    st.markdown('<hr class="card-title-divider">', unsafe_allow_html=True)
    st.markdown("### 게임별 정책 대응 현황")
    st.dataframe(build_game_summary(df), hide_index=True, use_container_width=True)


def render_daily_chart(df: pd.DataFrame, days: int) -> None:
    today = datetime.now(KST).date()
    keys = [(today - timedelta(days=i)) for i in range(days - 1, -1, -1)]
    daily = pd.DataFrame({"date_obj": keys})
    daily["date"] = daily["date_obj"].map(lambda x: x.strftime("%Y-%m-%d"))
    source = df.copy()
    daily["신규 접수"] = daily["date"].map(source["date"].value_counts()).fillna(0).astype(int)
    done = source[source["status"].str.contains("완료", na=False)]["date"].value_counts()
    pending = source[source["status"].str.contains("미대응", na=False)]["date"].value_counts()
    daily["처리 완료"] = daily["date"].map(done).fillna(0).astype(int)
    daily["미처리"] = daily["date"].map(pending).fillna(0).astype(int)

    fig = px.line(
        daily,
        x="date",
        y=["신규 접수", "처리 완료", "미처리"],
        markers=True,
        color_discrete_map={"신규 접수": "#4f6ef7", "처리 완료": "#38a169", "미처리": "#e53e3e"},
    )
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)


def render_deadline_risk_table(df: pd.DataFrame) -> None:
    active = df[~df["status"].str.contains("완료", na=False)].copy()
    if active.empty:
        st.success("미완료 항목이 없습니다.")
        return

    active["_dday"] = active["deadline"].map(calc_dday)
    buckets = [
        ("기한 경과", active[active["_dday"].notna() & (active["_dday"] < 0)], "이미 데드라인이 지난 항목"),
        ("D-Day", active[active["_dday"] == 0], "오늘 처리 필요"),
        ("D-3 이내", active[active["_dday"].between(1, 3, inclusive="both")], "3일 안에 처리 필요"),
        ("D-7 이내", active[active["_dday"].between(4, 7, inclusive="both")], "이번 주 안에 확인 필요"),
        ("D-30 이내", active[active["_dday"].between(8, 30, inclusive="both")], "30일 안에 도래"),
        ("데드라인 없음", active[active["_dday"].isna()], "데드라인 확인 필요"),
    ]

    rows = []
    for label, bucket, note in buckets:
        urgent_count = int((bucket["severity"] == "긴급").sum()) if not bucket.empty else 0
        pending_count = int(bucket["status"].str.contains("미대응", na=False).sum()) if not bucket.empty else 0
        unassigned_count = int((bucket["assignee"].fillna("").str.strip() == "").sum()) if not bucket.empty else 0
        nearest = "-"
        sample = "-"
        if not bucket.empty:
            sortable = bucket.copy()
            sortable["_sort"] = sortable["_dday"].fillna(9999)
            first = sortable.sort_values(["_sort", "date"], ascending=[True, False]).iloc[0]
            nearest = dday_text(first["deadline"]) or "-"
            sample_title = str(first["title"] or "-")
            sample = sample_title[:54] + ("..." if len(sample_title) > 54 else "")

        rows.append(
            {
                "리스크 구간": label,
                "건수": len(bucket),
                "긴급": urgent_count,
                "미대응": pending_count,
                "담당자 미지정": unassigned_count,
                "가장 가까운 일정": nearest,
                "대표 항목": sample,
                "메모": note,
            }
        )

    risk_df = pd.DataFrame(rows)
    st.dataframe(
        risk_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "건수": st.column_config.NumberColumn("건수", format="%d건"),
            "긴급": st.column_config.NumberColumn("긴급", format="%d건"),
            "미대응": st.column_config.NumberColumn("미대응", format="%d건"),
            "담당자 미지정": st.column_config.NumberColumn("담당자 미지정", format="%d건"),
        },
    )


def render_platform_severity_matrix(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    matrix = (
        pd.crosstab(df["platform"], df["severity"])
        .reindex(index=PLATFORM_VALUES, fill_value=0)
        .reindex(columns=SEVERITY_VALUES, fill_value=0)
    )
    matrix["합계"] = matrix.sum(axis=1)
    matrix["긴급 비율"] = matrix.apply(
        lambda row: f"{round((row['긴급'] / row['합계']) * 100, 1)}%" if row["합계"] else "0%",
        axis=1,
    )
    matrix = matrix.reset_index().rename(columns={"platform": "플랫폼"})

    st.dataframe(
        matrix,
        hide_index=True,
        use_container_width=True,
        column_config={
            "긴급": st.column_config.NumberColumn("🔴 긴급", format="%d건"),
            "주의": st.column_config.NumberColumn("🟠 주의", format="%d건"),
            "참고": st.column_config.NumberColumn("🟢 참고", format="%d건"),
            "합계": st.column_config.NumberColumn("합계", format="%d건"),
        },
    )


def render_small_list(df: pd.DataFrame, clickable: bool = False) -> None:
    if df.empty:
        st.caption("해당 항목 없음")
        return
    for _, row in df.iterrows():
        card_html = (
            f"""
            <div class="card {'urgent' if row['severity'] == '긴급' else 'warning' if row['severity'] == '주의' else ''}">
              <div>{platform_badge(row['platform'])}{severity_badge(row['severity'])}{status_badge(row['status'])}</div>
              <div class="title">{escape(str(row['title'] or '(제목 없음)'))}</div>
              <div class="muted">{row['date']} · {row['deadline']} {dday_badge(row['deadline'])}</div>
            </div>
            """
        )
        if clickable:
            st.markdown(
                f'<a class="overview-card-link" href="?page=response&selected_row={int(row["row_number"])}">{card_html}</a>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(card_html, unsafe_allow_html=True)


def build_game_summary(df: pd.DataFrame) -> pd.DataFrame:
    game_map = {
        "뉴맞고": "뉴맞고",
        "맞고": "뉴맞고",
        "섯다": "섯다",
        "포커": "포커",
        "뉴베가스": "뉴베가스",
        "베가스": "뉴베가스",
        "뉴고스톱": "뉴고스톱",
        "고스톱": "뉴고스톱",
        "홀덤": "홀덤",
        "쇼다운": "홀덤",
    }
    rows = []
    for game in ["뉴맞고", "섯다", "포커", "뉴베가스", "뉴고스톱", "홀덤", "기타"]:
        matched = []
        for _, row in df.iterrows():
            title = str(row["title"]).lower()
            game_name = "기타"
            for key, value in game_map.items():
                if key in title:
                    game_name = value
            if game_name == game:
                matched.append(row)
        gdf = pd.DataFrame(matched)
        if gdf.empty:
            continue
        latest = gdf.sort_values("date", ascending=False).iloc[0]["title"]
        rows.append(
            {
                "게임명": game,
                "전체": len(gdf),
                "완료": int(gdf["status"].str.contains("완료", na=False).sum()),
                "진행 중": int(gdf["status"].str.contains("진행", na=False).sum()),
                "검토 전": int(gdf["status"].str.contains("검토", na=False).sum()),
                "미대응": int(gdf["status"].str.contains("미대응", na=False).sum()),
                "긴급": int((gdf["severity"] == "긴급").sum()),
                "최근 이슈": latest[:48] + ("..." if len(latest) > 48 else ""),
            }
        )
    return pd.DataFrame(rows)


def render_response(df: pd.DataFrame) -> None:
    if st.session_state.pop("_reset_response_filters_requested", False):
        reset_dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        if reset_dates.empty:
            today = date.today()
            reset_response_filters(today, today)
        else:
            reset_response_filters(reset_dates.min().date(), reset_dates.max().date())

    with st.sidebar:
        st.divider()
        st.markdown("### 📅 기간 선택")
        min_date = parse_date_input(df["date"].min()) if not df.empty else datetime.now(KST).date()
        max_date = parse_date_input(df["date"].max()) if not df.empty else datetime.now(KST).date()
        if "date_filter" not in st.session_state:
            st.session_state["date_filter"] = (min_date, max_date)
        st.date_input(
            "조회 기간",
            value=st.session_state["date_filter"],
            min_value=min_date,
            max_value=max_date,
            format="YYYY/MM/DD",
            key="date_filter",
        )
        st.divider()
        st.markdown("### 필터")
        st.selectbox("심각도", ["전체", "긴급", "주의", "참고", "미대응"], key="stat_filter")
        st.selectbox("플랫폼", ["전체"] + PLATFORM_VALUES, key="platform_filter")
        st.selectbox("상태", ["전체", "미대응", "검토 전", "진행 중", "완료"], key="status_filter")
        st.text_input("검색", placeholder="제목, 플랫폼, 담당자 검색", key="search_query")
        st.selectbox("정렬", ["날짜 최신순", "날짜 오래된순", "심각도 높은순", "데드라인 임박순"], key="sort_option")
        if st.button("필터 초기화", use_container_width=True):
            st.session_state["date_filter"] = (min_date, max_date)
            st.session_state["stat_filter"] = "전체"
            st.session_state["platform_filter"] = "전체"
            st.session_state["status_filter"] = "전체"
            st.session_state["response_status_tab"] = "전체"
            st.session_state["search_query"] = ""
            st.session_state["sort_option"] = "날짜 최신순"
            st.session_state["response_page"] = 1
            st.rerun()
        st.divider()
        st.markdown("**데드라인 임박**")
        deadline_items = df[
            df["deadline"].map(lambda x: (calc_dday(x) is not None) and 0 <= calc_dday(x) <= 30)
            & ~df["status"].str.contains("완료", na=False)
        ].copy()
        deadline_items["_dday"] = deadline_items["deadline"].map(calc_dday)
        deadline_items = deadline_items.sort_values("_dday").head(5)
        if deadline_items.empty:
            st.caption("임박 항목 없음")
        for _, row in deadline_items.iterrows():
            if st.button(
                f"{dday_text(row['deadline'])} · {row['title'][:28]}",
                key=f"deadline-jump-{row['row_number']}",
                use_container_width=True,
            ):
                st.session_state["jump_to_row"] = int(row["row_number"])
                st.session_state["current_page"] = "대응 현황"
                st.rerun()
            st.caption(f"{row['platform']} · {row['deadline']}")

        st.divider()
    st.markdown("### 요약")
    m1, m2 = st.sidebar.columns(2)
    m1.metric("전체", len(df))
    m2.metric("긴급", int((df["severity"] == "긴급").sum()))
    m3, m4 = st.sidebar.columns(2)
    if True:
        m3.metric("주의", int((df["severity"] == "주의").sum()))
        m4.metric("미대응", int(df["status"].str.contains("미대응", na=False).sum()))

    filtered = apply_filters(df)
    jump_to_row = st.session_state.pop("jump_to_row", None)
    if jump_to_row:
        match = filtered.reset_index(drop=True)
        positions = match.index[match["row_number"] == jump_to_row].tolist()
        if positions:
            page_size_for_jump = int(st.session_state.get("response_page_size", 30))
            st.session_state["response_page"] = positions[0] // page_size_for_jump + 1
            st.session_state[f"open-policy-{jump_to_row}"] = True
            st.session_state["scroll_to_row"] = int(jump_to_row)
            st.session_state["highlight_row"] = int(jump_to_row)

    page_size, page, total_pages = render_response_pagination(len(filtered), len(df))
    render_response_status_tabs()
    st.markdown('<hr class="card-title-divider">', unsafe_allow_html=True)
    start = (page - 1) * page_size
    page_df = filtered.iloc[start : start + page_size]

    st.caption(f"{len(filtered)} / {len(df)}건 · {page}/{total_pages} 페이지")
    if page_df.empty:
        st.info("해당 조건의 데이터가 없습니다.")
        return

    st.markdown('<div class="list-hint">항목을 클릭하면 바로 아래에 상세 정보와 수정 영역이 펼쳐집니다.</div>', unsafe_allow_html=True)
    for _, row in page_df.iterrows():
        render_policy_expander(row)
    render_scroll_to_target()
    if st.session_state.get("highlight_row"):
        st.session_state.pop("highlight_row", None)


def render_response_pagination(filtered_count: int, total_count: int) -> tuple[int, int, int]:
    if "response_page_size" not in st.session_state:
        st.session_state["response_page_size"] = 30
    if "response_page" not in st.session_state:
        st.session_state["response_page"] = 1

    page_size = int(st.session_state["response_page_size"])
    total_pages = max(1, (filtered_count + page_size - 1) // page_size)
    st.session_state["response_page"] = min(max(1, int(st.session_state["response_page"])), total_pages)
    page = int(st.session_state["response_page"])

    start = 0 if filtered_count == 0 else (page - 1) * page_size + 1
    end = min(page * page_size, filtered_count)

    with st.container():
        cols = st.columns([0.12, 0.045, 0.045, 0.045, 0.12, 0.035, 0.035, 0.035, 0.035, 0.035, 0.035, 0.035, 0.035, 0.035, 0.035, 0.035, 0.25])
        cols[0].markdown(f"**정책 알림** &nbsp; :gray[{total_count}건]")

        for idx, size in enumerate([30, 50, 100], start=1):
            if cols[idx].button(str(size), key=f"page-size-{size}", type="primary" if page_size == size else "secondary", use_container_width=True):
                st.session_state["response_page_size"] = size
                st.session_state["response_page"] = 1
                st.rerun()

        cols[4].markdown(f":gray[{start}-{end} / {filtered_count}건]")

        if cols[5].button("«", key="page-first", disabled=page <= 1, use_container_width=True):
            st.session_state["response_page"] = 1
            st.rerun()
        if cols[6].button("‹", key="page-prev", disabled=page <= 1, use_container_width=True):
            st.session_state["response_page"] = page - 1
            st.rerun()

        page_buttons = build_page_buttons(page, total_pages)
        col_idx = 7
        ellipsis_idx = 0
        for item in page_buttons:
            if item == "...":
                ellipsis_idx += 1
                cols[col_idx].markdown(":gray[...]")
            else:
                if cols[col_idx].button(str(item), key=f"page-{item}", type="primary" if item == page else "secondary", use_container_width=True):
                    st.session_state["response_page"] = int(item)
                    st.rerun()
            col_idx += 1
            if col_idx >= 14:
                break

        if cols[14].button("›", key="page-next", disabled=page >= total_pages, use_container_width=True):
            st.session_state["response_page"] = page + 1
            st.rerun()
        if cols[15].button("»", key="page-last", disabled=page >= total_pages, use_container_width=True):
            st.session_state["response_page"] = total_pages
            st.rerun()

    return page_size, page, total_pages


def render_response_status_tabs() -> None:
    if "response_status_tab" not in st.session_state:
        st.session_state["response_status_tab"] = "전체"

    st.markdown('<div class="status-tabs-spacer"></div>', unsafe_allow_html=True)
    tabs = ["전체", "검토 전", "진행 중", "완료", "미대응"]
    labels = {
        "전체": "전체",
        "검토 전": "📋 검토 전",
        "진행 중": "🔄 진행 중",
        "완료": "✅ 완료",
        "미대응": "❌ 미대응",
    }
    cols = st.columns([0.07, 0.08, 0.08, 0.07, 0.08, 0.62])
    for idx, tab in enumerate(tabs):
        active = st.session_state["response_status_tab"] == tab
        if cols[idx].button(
            labels[tab],
            key=f"response-status-tab-{tab}",
            type="primary" if active else "secondary",
            use_container_width=True,
        ):
            st.session_state["response_status_tab"] = tab
            st.session_state["response_page"] = 1
            st.rerun()


def build_page_buttons(page: int, total_pages: int) -> list[int | str]:
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    if page <= 4:
        return [1, 2, 3, 4, 5, "...", total_pages]
    if page >= total_pages - 3:
        return [1, "...", total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
    return [1, "...", page - 1, page, page + 1, "...", total_pages]


def render_policy_expander(row: pd.Series) -> None:
    row_number = int(row["row_number"])
    toggle_key = f"open-policy-{row_number}"
    if st.session_state.get("close_policy_after_save") == row_number:
        st.session_state[toggle_key] = False
        st.session_state.pop("close_policy_after_save", None)

    st.markdown(f'<div id="policy-row-{int(row["row_number"])}"></div>', unsafe_allow_html=True)
    header_col, toggle_col = st.columns([0.82, 0.18], vertical_alignment="top")
    with header_col:
        st.markdown(build_summary_card_html(row), unsafe_allow_html=True)
    with toggle_col:
        open_detail = st.toggle("상세/수정", key=toggle_key)
    if open_detail:
        with st.container(border=True):
            st.markdown('<hr class="card-soft-divider">', unsafe_allow_html=True)
            info_col, action_col = st.columns([0.45, 0.55], gap="large")
            with info_col:
                st.markdown("#### 기본 정보")
                st.markdown(
                    f"""
                    <div class="detail-row"><span class="detail-key">날짜</span><span class="detail-val">{row['date']}</span></div>
                    <div class="detail-row"><span class="detail-key">플랫폼</span><span class="detail-val">{platform_badge(row['platform'])}</span></div>
                    <div class="detail-row"><span class="detail-key">심각도</span><span class="detail-val">{severity_badge(row['severity'])}</span></div>
                    <div class="detail-row"><span class="detail-key">대응 상태</span><span class="detail-val">{status_badge(row['status'])}</span></div>
                    <div class="detail-row"><span class="detail-key">담당자</span><span class="detail-val">{escape(str(row['assignee'] or '-'))}</span></div>
                    <div class="detail-row"><span class="detail-key">데드라인</span><span class="detail-val">{row['deadline'] or '-'}</span></div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown('<hr class="card-soft-divider">', unsafe_allow_html=True)
                st.markdown("#### 링크")
                url = gmail_search_url(str(row["title"] or ""))
                if url:
                    st.link_button("📧 Gmail 원문 보기", url, use_container_width=True)
                st.button("🔍 정책 내용 요약 보기 (준비중)", disabled=True, use_container_width=True, key=f"summary-disabled-{row['row_number']}")

            with action_col:
                st.markdown("#### 대응 현황")
                with st.form(f"inline-edit-form-{row['row_number']}"):
                    severity = st.selectbox(
                        "심각도",
                        SEVERITY_VALUES,
                        index=SEVERITY_VALUES.index(row["severity"]) if row["severity"] in SEVERITY_VALUES else 2,
                        key=f"inline-severity-{row['row_number']}",
                    )
                    current_deadline = parse_date_input(row["deadline"])
                    deadline = st.date_input(
                        "데드라인",
                        value=current_deadline,
                        format="YYYY-MM-DD",
                        key=f"inline-deadline-{row['row_number']}",
                    )
                    status = st.selectbox(
                        "대응 상태",
                        STATUS_VALUES,
                        index=STATUS_VALUES.index(row["status"]) if row["status"] in STATUS_VALUES else 1,
                        key=f"inline-status-{row['row_number']}",
                    )
                    assignee = st.text_input("담당자", value=str(row["assignee"] or ""), key=f"inline-assignee-{row['row_number']}")
                    memo = st.text_area("메모", value=str(row["memo"] or ""), height=110, key=f"inline-memo-{row['row_number']}")
                    submitted = st.form_submit_button("💾 저장", use_container_width=True)

                if submitted:
                    payload = {
                        "severity": severity,
                        "deadline": deadline.strftime("%Y-%m-%d") if deadline else "-",
                        "status": status,
                        "assignee": assignee,
                        "memo": memo,
                    }
                    ok, result = update_row(
                        int(row["row_number"]),
                        payload,
                        str(row.get("lastModified", "") or ""),
                    )
                    if ok:
                        st.session_state["toast_message"] = "저장 완료"
                        st.session_state["close_policy_after_save"] = int(row["row_number"])
                        st.rerun()
                    elif result == "conflict":
                        st.error("다른 곳에서 먼저 수정된 항목입니다. 새로고침 후 다시 확인해주세요.")
                    else:
                        st.error("저장에 실패했습니다.")


def render_scroll_to_target() -> None:
    target = st.session_state.pop("scroll_to_row", None)
    if not target:
        return
    components.html(
        f"""
        <script>
        const targetId = "policy-row-{int(target)}";
        const scrollToTarget = () => {{
          const el = window.parent.document.getElementById(targetId);
          if (el) {{
            el.scrollIntoView({{ behavior: "smooth", block: "center" }});
          }}
        }};
        setTimeout(scrollToTarget, 250);
        setTimeout(scrollToTarget, 700);
        </script>
        """,
        height=0,
    )


def build_summary_card_html(row: pd.Series) -> str:
    status_class = status_card_class(row["status"])
    highlight_class = " jump-highlight" if st.session_state.get("highlight_row") == int(row["row_number"]) else ""
    new_badge = '<span class="badge pb-default">NEW</span>' if is_new(row["date"]) else ""
    update_badge = needs_update_badge(row)
    meta_items = [
        ("날짜", row["date"] or "-"),
        ("플랫폼", row["platform"] or "-"),
        ("심각도", row["severity"] or "-"),
        ("상태", row["status"] or "-"),
        ("데드라인", row["deadline"] or "-"),
        ("담당자", row["assignee"] or "담당자 미지정"),
    ]
    meta_html = "".join(
        f'<span class="policy-card-meta-item">'
        f'<span class="policy-card-meta-label">{escape(str(label))}</span>'
        f'<span class="policy-card-meta-value">{escape(str(value))}</span>'
        f'</span>'
        for label, value in meta_items
    )
    return (
        f'<div class="policy-summary-card {status_class}{highlight_class}">'
        f'<div class="policy-card-title">{escape(str(row["title"] or "(제목 없음)"))}</div>'
        f'<div class="policy-card-tags">'
        f'{platform_badge(row["platform"])}'
        f'{severity_badge(row["severity"])}'
        f'{status_badge(row["status"])}'
        f'{dday_badge(row["deadline"])}'
        f'{new_badge}'
        f'{update_badge}'
        f'</div>'
        f'<div class="policy-card-meta">{meta_html}</div>'
        f'</div>'
    )


def status_card_class(status: str) -> str:
    text = str(status or "")
    if "완료" in text:
        return "status-done"
    if "진행" in text:
        return "status-progress"
    if "미대응" in text:
        return "status-pending"
    return "status-review"


def build_expander_summary(row: pd.Series) -> str:
    dday = dday_text(row["deadline"])
    dday_part = f"  ⏰ {dday}" if dday else ""
    new_part = "  🔵 NEW" if is_new(row["date"]) else ""
    assignee = row["assignee"] or "담당자 미지정"
    title = str(row["title"] or "(제목 없음)")
    return (
        f"{platform_tag_text(row['platform'])}  "
        f"{severity_tag_text(row['severity'])}  "
        f"{status_tag_text(row['status'])}  "
        f"{title}{dday_part}{new_part}  "
        f"👤 {assignee}"
    )


def platform_tag_text(platform: str) -> str:
    return {
        "애플": "🟣 애플",
        "구글": "🔵 구글",
        "Firebase": "🟡 Firebase",
        "기타": "⚪ 기타",
    }.get(platform or "기타", "⚪ 기타")


def severity_tag_text(severity: str) -> str:
    return {
        "긴급": "🔴 긴급",
        "주의": "🟠 주의",
        "참고": "🟢 참고",
    }.get(severity or "참고", "🟢 참고")


def status_tag_text(status: str) -> str:
    if "완료" in str(status):
        return "✅ 완료"
    if "진행" in str(status):
        return "🔄 진행 중"
    if "미대응" in str(status):
        return "❌ 미대응"
    return "📋 검토 전"


def render_policy_table(page_df: pd.DataFrame) -> int | None:
    table = page_df.copy().reset_index(drop=True)
    table["선택"] = "›"
    table["알림"] = table.apply(build_policy_line, axis=1)
    table["D-Day"] = table["deadline"].map(dday_text)
    view = table[["선택", "알림", "platform", "severity", "status", "date", "deadline", "assignee", "row_number"]].rename(
        columns={
            "platform": "플랫폼",
            "severity": "심각도",
            "status": "상태",
            "date": "날짜",
            "deadline": "데드라인",
            "assignee": "담당자",
            "row_number": "_row_number",
        }
    )

    st.markdown('<div class="list-hint">행을 클릭하면 오른쪽에서 상세 내용을 수정할 수 있습니다.</div>', unsafe_allow_html=True)
    event = st.dataframe(
        view,
        hide_index=True,
        use_container_width=True,
        height=min(760, 42 * (len(view) + 1)),
        column_config={
            "선택": st.column_config.TextColumn(" ", width="small"),
            "알림": st.column_config.TextColumn("정책 알림", width="large"),
            "플랫폼": st.column_config.TextColumn("플랫폼", width="small"),
            "심각도": st.column_config.TextColumn("심각도", width="small"),
            "상태": st.column_config.TextColumn("상태", width="small"),
            "날짜": st.column_config.TextColumn("날짜", width="small"),
            "데드라인": st.column_config.TextColumn("데드라인", width="small"),
            "담당자": st.column_config.TextColumn("담당자", width="small"),
            "_row_number": None,
        },
        on_select="rerun",
        selection_mode="single-row",
        key="policy_table",
    )

    selected_rows = event.selection.rows if event and event.selection else []
    if selected_rows:
        selected_idx = selected_rows[0]
        row_number = int(view.iloc[selected_idx]["_row_number"])
        st.session_state["opened_last_modified"] = str(table.iloc[selected_idx].get("lastModified", "") or "")
        return row_number
    return st.session_state.get("selected_response_row")


def build_policy_line(row: pd.Series) -> str:
    dday = dday_text(row["deadline"])
    dday_part = f" | {dday}" if dday else ""
    new_part = " | NEW" if is_new(row["date"]) else ""
    title = str(row["title"] or "(제목 없음)")
    assignee = str(row["assignee"] or "담당자 미지정")
    return f"{title}{dday_part}{new_part} | {assignee}"


def render_response_drawer(row: pd.Series) -> None:
    st.markdown('<div class="drawer-panel">', unsafe_allow_html=True)
    close_col, title_col = st.columns([0.14, 0.86])
    with close_col:
        if st.button("×", key="close-response-drawer", use_container_width=True):
            st.session_state.pop("selected_response_row", None)
            st.rerun()
    with title_col:
        st.markdown(
            f'<div class="drawer-title">{escape(str(row["title"] or "(제목 없음)"))}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("**기본 정보**")
    st.markdown(
        f"""
        <div class="detail-row"><span class="detail-key">날짜</span><span class="detail-val">{row['date']}</span></div>
        <div class="detail-row"><span class="detail-key">플랫폼</span><span class="detail-val">{platform_badge(row['platform'])}</span></div>
        <div class="detail-row"><span class="detail-key">심각도</span><span class="detail-val">{severity_badge(row['severity'])}</span></div>
        <div class="detail-row"><span class="detail-key">대응 상태</span><span class="detail-val">{status_badge(row['status'])}</span></div>
        <div class="detail-row"><span class="detail-key">담당자</span><span class="detail-val">{escape(str(row['assignee'] or '-'))}</span></div>
        <div class="detail-row"><span class="detail-key">데드라인</span><span class="detail-val">{row['deadline'] or '-'}</span></div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("**링크**")
    url = gmail_search_url(str(row["title"] or ""))
    if url:
        st.link_button("📧 Gmail 원문 보기", url, use_container_width=True)
    st.button("🔍 정책 내용 요약 보기 (준비중)", disabled=True, use_container_width=True)

    st.markdown("**대응 현황**")
    with st.form(f"response-drawer-form-{row['row_number']}"):
        severity = st.selectbox(
            "심각도",
            SEVERITY_VALUES,
            index=SEVERITY_VALUES.index(row["severity"]) if row["severity"] in SEVERITY_VALUES else 2,
        )
        current_deadline = "" if row["deadline"] == "-" else str(row["deadline"] or "")
        deadline = st.text_input("데드라인", value=current_deadline, placeholder="YYYY-MM-DD")
        status = st.selectbox(
            "대응 상태",
            STATUS_VALUES,
            index=STATUS_VALUES.index(row["status"]) if row["status"] in STATUS_VALUES else 1,
        )
        assignee = st.text_input("담당자", value=str(row["assignee"] or ""))
        memo = st.text_area("메모", value=str(row["memo"] or ""), height=120)
        submitted = st.form_submit_button("💾 저장", use_container_width=True)

    if submitted:
        payload = {
            "severity": severity,
            "deadline": deadline or "-",
            "status": status,
            "assignee": assignee,
            "memo": memo,
        }
        ok, result = update_row(
            int(row["row_number"]),
            payload,
            st.session_state.get("opened_last_modified", str(row.get("lastModified", "") or "")),
        )
        if ok:
            st.success("저장 완료")
            st.session_state["opened_last_modified"] = result
            st.rerun()
        elif result == "conflict":
            st.error("다른 곳에서 먼저 수정된 항목입니다. 새로고침 후 다시 확인해주세요.")
        else:
            st.error("저장에 실패했습니다.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_policy_card(row: pd.Series, compact: bool = False) -> None:
    sev_class = "urgent" if row["severity"] == "긴급" else "warning" if row["severity"] == "주의" else ""
    st.markdown(
        f"""
        <div class="card {sev_class}">
          <div>
            {platform_badge(row['platform'])}
            {severity_badge(row['severity'])}
            {status_badge(row['status'])}
            {dday_badge(row['deadline'])}
            {'<span class="badge pb-default">NEW</span>' if is_new(row['date']) else ''}
          </div>
          <div class="title">{escape(str(row['title'] or '(제목 없음)'))}</div>
          <div class="muted">{row['date']} · 담당자 {row['assignee'] or '-'} · 데드라인 {row['deadline'] or '-'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns([0.18, 0.18, 0.64]) if compact else st.columns([0.12, 0.12, 0.76])
    with cols[0]:
        if st.button("수정", key=f"edit-{row['row_number']}-{compact}", use_container_width=True):
            st.session_state["editing_row"] = int(row["row_number"])
            st.session_state["opened_last_modified"] = str(row.get("lastModified", "") or "")
            st.rerun()
    with cols[1]:
        url = gmail_search_url(str(row["title"] or ""))
        if url:
            st.link_button("원문", url, use_container_width=True)


def render_overview_action_card(row: pd.Series) -> None:
    st.markdown(build_overview_card_html(row), unsafe_allow_html=True)
    if st.button("대응 현황에서 열기", key=f"overview-open-{row['row_number']}", use_container_width=True):
        st.session_state["pending_page"] = "대응 현황"
        st.session_state["jump_to_row"] = int(row["row_number"])
        st.rerun()


def render_overview_urgent_line(row: pd.Series) -> None:
    st.markdown(build_urgent_line_html(row), unsafe_allow_html=True)


def build_urgent_line_html(row: pd.Series) -> str:
    dday = dday_text(row["deadline"])
    dday_part = f" | ⏰ {dday}" if dday else ""
    assignee = escape(str(row["assignee"] or "담당자 미지정"))
    return (
        f'<a class="urgent-line" href="?page=response&selected_row={int(row["row_number"])}">'
        f'<span>›</span>'
        f'{platform_badge(row["platform"])}'
        f'{severity_badge(row["severity"])}'
        f'{status_badge(row["status"])}'
        f'<span class="urgent-line-title">{escape(str(row["title"] or "(제목 없음)"))}</span>'
        f'<span class="urgent-line-meta">{row["date"]} · {assignee}{dday_part}</span>'
        f'</a>'
    )


def build_overview_card_html(row: pd.Series) -> str:
    status_class = status_card_class(row["status"])
    new_badge = '<span class="badge pb-default">NEW</span>' if is_new(row["date"]) else ""
    return (
        f'<div class="policy-summary-card {status_class}" style="min-height:58px; padding:10px 12px; transition: transform .16s ease, box-shadow .18s ease;">'
        f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">'
        f'{platform_badge(row["platform"])}'
        f'{severity_badge(row["severity"])}'
        f'{status_badge(row["status"])}'
        f'{dday_badge(row["deadline"])}'
        f'{new_badge}'
        f'<span style="font-weight:800;color:#1a202c;margin-left:4px;">{escape(str(row["title"] or "(제목 없음)"))}</span>'
        f'</div>'
        f'<div class="muted" style="margin-top:4px;">{row["date"]} · 담당자 {escape(str(row["assignee"] or "-"))} · 데드라인 {row["deadline"] or "-"}</div>'
        f'</div>'
    )


def render_editor(df: pd.DataFrame) -> None:
    editing_row = st.session_state.get("editing_row")
    if not editing_row:
        return

    source = df[df["row_number"] == editing_row]
    if source.empty:
        st.warning("선택한 항목을 찾을 수 없습니다. 새로고침 후 다시 시도해주세요.")
        st.session_state.pop("editing_row", None)
        return

    row = source.iloc[0]
    with st.sidebar:
        st.header("정책 알림 수정")
        st.caption(row["title"])
        st.markdown(
            f"{platform_badge(row['platform'])}{severity_badge(row['severity'])}{status_badge(row['status'])}",
            unsafe_allow_html=True,
        )
        st.write(f"날짜: {row['date']}")
        st.write(f"데드라인: {row['deadline']} {dday_text(row['deadline'])}")
        if row.get("memo"):
            st.info(str(row["memo"]))

        with st.form("edit_form"):
            severity = st.selectbox("심각도", SEVERITY_VALUES, index=SEVERITY_VALUES.index(row["severity"]) if row["severity"] in SEVERITY_VALUES else 2)
            current_deadline = "" if row["deadline"] == "-" else row["deadline"]
            deadline = st.text_input("데드라인", value=current_deadline, placeholder="YYYY-MM-DD")
            status = st.selectbox("대응 상태", STATUS_VALUES, index=STATUS_VALUES.index(row["status"]) if row["status"] in STATUS_VALUES else 1)
            assignee = st.text_input("담당자", value=str(row["assignee"] or ""))
            memo = st.text_area("메모", value=str(row["memo"] or ""), height=120)
            submitted = st.form_submit_button("구글 시트에 저장", use_container_width=True)

        if submitted:
            payload = {
                "severity": severity,
                "deadline": deadline or "-",
                "status": status,
                "assignee": assignee,
                "memo": memo,
            }
            ok, result = update_row(editing_row, payload, st.session_state.get("opened_last_modified", ""))
            if ok:
                st.session_state["toast_message"] = "저장 완료"
                st.session_state.pop("editing_row", None)
                st.session_state.pop("opened_last_modified", None)
                st.rerun()
            elif result == "conflict":
                st.error("다른 곳에서 먼저 수정된 항목입니다. 새로고침 후 다시 확인해주세요.")
            else:
                st.error("저장에 실패했습니다.")

        if st.button("닫기", use_container_width=True):
            st.session_state.pop("editing_row", None)
            st.rerun()


def main() -> None:
    require_neowiz_login()

    inject_style()
    df = load_data()
    toast_message = st.session_state.pop("toast_message", None)
    if toast_message:
        st.markdown(
            f'<div class="success-toast">✅ {escape(str(toast_message))}</div>',
            unsafe_allow_html=True,
        )
    target_page = st.query_params.get("page")
    target_row = st.query_params.get("selected_row")
    if isinstance(target_page, list):
        target_page = target_page[0] if target_page else None
    if isinstance(target_row, list):
        target_row = target_row[0] if target_row else None
    if target_row:
        try:
            st.session_state["jump_to_row"] = int(target_row)
            st.session_state["current_page"] = "대응 현황"
        except ValueError:
            pass
        st.query_params.clear()
    pending_page = st.session_state.pop("pending_page", None)

    with st.sidebar:
        st.markdown("### 대시보드 메뉴")
        default_page = pending_page or st.session_state.get("current_page") or ("대응 현황" if target_page == "response" else "현황")
        page = st.radio(
            "메뉴",
            ["현황", "대응 현황"],
            index=["현황", "대응 현황"].index(default_page),
            label_visibility="collapsed",
            key="page_radio",
        )
        st.session_state["current_page"] = page

    render_header(df)
    render_editor(df)

    if page == "현황":
        render_overview(df)
    else:
        render_response(df)


if __name__ == "__main__":
    main()
