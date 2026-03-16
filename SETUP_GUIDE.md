# 네이버 지식인 모니터링 봇 — 설치 및 설정 가이드

## 목차
1. [Python 설치](#1-python-설치)
2. [프로젝트 다운로드 및 패키지 설치](#2-프로젝트-다운로드-및-패키지-설치)
3. [Google Sheets API 서비스 계정 설정](#3-google-sheets-api-서비스-계정-설정)
4. [구글 시트 준비](#4-구글-시트-준비)
5. [봇 설정 (config.py)](#5-봇-설정-configpy)
6. [실행 방법](#6-실행-방법)
7. [문제 해결](#7-문제-해결)

---

## 1. Python 설치

1. [python.org](https://www.python.org/downloads/) 에서 **Python 3.10 이상**을 다운로드합니다.
2. 설치 시 **"Add Python to PATH"** 체크박스를 반드시 선택합니다.
3. 설치 후 터미널(명령 프롬프트)에서 확인:
   ```
   python --version
   ```
   `Python 3.10.x` 이상이 표시되면 성공입니다.

---

## 2. 프로젝트 다운로드 및 패키지 설치

터미널에서 아래 명령어를 순서대로 실행합니다:

```bash
# 1) 프로젝트 폴더로 이동
cd kin.naver.com

# 2) 가상환경 생성 (권장)
python -m venv venv

# 3) 가상환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4) 패키지 설치
pip install -r requirements.txt

# 5) Playwright 브라우저 설치 (Chromium)
playwright install chromium
```

---

## 3. Google Sheets API 서비스 계정 설정

이 부분이 가장 중요합니다. 아래 단계를 정확히 따라해 주세요.

### 3-1. Google Cloud 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 에 접속합니다.
2. 상단의 프로젝트 선택 드롭다운 → **"새 프로젝트"** 클릭
3. 프로젝트 이름: `naver-kin-monitor` (원하는 이름)
4. **"만들기"** 클릭

### 3-2. API 활성화

1. 좌측 메뉴 → **"API 및 서비스"** → **"라이브러리"**
2. 검색창에 `Google Sheets API` 검색 → 클릭 → **"사용"** 버튼 클릭
3. 다시 검색창에 `Google Drive API` 검색 → 클릭 → **"사용"** 버튼 클릭

> ⚠️ **두 API 모두 활성화해야 합니다!**

### 3-3. 서비스 계정 생성

1. 좌측 메뉴 → **"API 및 서비스"** → **"사용자 인증 정보"**
2. 상단 **"+ 사용자 인증 정보 만들기"** → **"서비스 계정"** 선택
3. 서비스 계정 이름: `kin-monitor` (원하는 이름)
4. **"만들고 계속하기"** → (역할 설정은 건너뛰기) → **"완료"**

### 3-4. JSON 키 파일 다운로드

1. 방금 만든 서비스 계정 이름을 클릭합니다.
2. 상단 탭 중 **"키"** 탭 클릭
3. **"키 추가"** → **"새 키 만들기"**
4. 키 유형: **JSON** 선택 → **"만들기"**
5. JSON 파일이 자동으로 다운로드됩니다.
6. **다운로드된 파일 이름을 `credentials.json`으로 변경**합니다.
7. `credentials.json` 파일을 프로젝트 폴더 (`kin.naver.com/`)에 넣습니다.

> ⚠️ `credentials.json` 파일은 절대 외부에 공유하지 마세요!

### 3-5. 서비스 계정 이메일 확인

다운로드한 `credentials.json` 파일을 열면 아래와 같은 이메일이 있습니다:

```
"client_email": "kin-monitor@프로젝트명.iam.gserviceaccount.com"
```

이 이메일 주소를 복사해 두세요. 다음 단계에서 필요합니다.

---

## 4. 구글 시트 준비

### 4-1. 시트 생성

1. [Google Sheets](https://sheets.google.com/) 접속
2. **빈 스프레드시트** 생성
3. 시트 이름을 원하는 이름으로 설정합니다.

### 4-2. 서비스 계정에 시트 공유

1. 시트 우측 상단 **"공유"** 버튼 클릭
2. 3-5에서 복사한 서비스 계정 이메일 주소 입력
3. 권한: **"편집자"** 선택
4. **"보내기"** 클릭

> 이 단계를 빠뜨리면 봇이 시트에 접근할 수 없습니다!

### 4-3. 키워드 입력 (시트에서 키워드를 읽어올 경우)

A열에 키워드를 입력합니다:

| A (키워드) |
|-----------|
| 키워드 |
| 인테리어 비용 |
| 집 리모델링 |
| 새집 인테리어 |
| ... (총 66개) |

1~3행은 헤더/제목이므로 **4번째 행부터** 키워드를 입력합니다. (config.py의 `KEYWORDS_START_ROW` 설정과 일치)

### 4-4. 시트 키 확인 (선택사항)

시트 URL이 아래와 같다면:
```
https://docs.google.com/spreadsheets/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit
```
`1aBcDeFgHiJkLmNoPqRsTuVwXyZ` 부분이 시트 키입니다.

`config.py`의 `SPREADSHEET_KEY`에 이 값을 입력하면 이름 대신 키로 시트를 찾습니다.

---

## 5. 봇 설정 (config.py)

`config.py` 파일을 열어 아래 항목을 확인/수정합니다:

```python
# 타겟 답변자 (확인할 네이버 지식인 답변자 닉네임)
TARGET_ANSWERER = "새집느낌"

# 구글 시트 설정
SPREADSHEET_KEY = "시트URL의키"  # 시트 URL에서 추출한 키

# 키워드 소스 (True: 시트에서 읽기, False: KEYWORDS 리스트 사용)
USE_SHEET_KEYWORDS = True
```

---

## 6. 실행 방법

```bash
# 가상환경 활성화 후
python naver_kin_monitor.py
```

### 실행 결과 확인
- 터미널에 진행 상황이 실시간으로 표시됩니다.
- `monitor.log` 파일에도 로그가 저장됩니다.
- 구글 시트에 결과가 자동으로 기록됩니다.

### 구글 시트 결과 양식

| 날짜 | 키워드 | 1위 게시물 순위 | 1위 게시물 링크 | 2위 게시물 순위 | 2위 게시물 링크 | 비고 |
|------|--------|---------------|---------------|---------------|---------------|------|
| 2024-01-15 10:30 | 인테리어 비용 | 3위 (1위: 홍길동) | https://... | 순위권 밖 | https://... | |

---

## 7. 문제 해결

### "구글 시트 연결 실패"
- `credentials.json` 파일이 프로젝트 폴더에 있는지 확인
- 시트를 서비스 계정 이메일에 **편집자** 권한으로 공유했는지 확인
- Google Sheets API와 Google Drive API가 모두 **활성화**되었는지 확인

### "검색 결과 없음"
- 네이버에서 IP가 차단되었을 수 있습니다. 잠시 후 재시도하세요.
- `config.py`에서 `HEADLESS = False`로 변경하여 브라우저를 직접 확인해 보세요.

### "Playwright 오류"
```bash
# 브라우저 재설치
playwright install chromium
```

### "키워드가 없습니다"
- `USE_SHEET_KEYWORDS = True`인 경우: 시트 A열에 키워드가 입력되어 있는지 확인
- `USE_SHEET_KEYWORDS = False`인 경우: `config.py`의 `KEYWORDS` 리스트에 키워드를 입력
