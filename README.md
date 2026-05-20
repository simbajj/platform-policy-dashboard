# 플랫폼 정책 대응 현황 Streamlit

Apps Script 대시보드와 같은 Google Sheet를 읽고 수정하는 Streamlit 버전입니다.

## 실행 준비

1. Python 패키지 설치

```powershell
pip install -r requirements.txt
```

2. Google Cloud 서비스 계정 키 준비

서비스 계정 이메일을 원본 Google Sheet에 `편집자`로 공유해야 합니다.

3. Streamlit secrets 설정

`.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사한 뒤 서비스 계정 JSON 값을 채웁니다.

## 실행

```powershell
streamlit run app.py
```

브라우저에 뜨는 로컬 주소에서 별도 Streamlit 페이지로 확인할 수 있습니다.

## 데이터 위치

- Spreadsheet ID: `1sAu5fcc3F1yv8fQSZO_zY_1IiAr0VVhnPfm3ah6xDN4`
- Sheet name: `시트1`

수정 저장 시 아래 칸을 업데이트합니다.

- `D:H`: 심각도, 데드라인, 대응상태, 담당자, 메모
- `K`: 최종수정
