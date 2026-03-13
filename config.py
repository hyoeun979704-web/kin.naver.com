"""
네이버 지식인 모니터링 봇 설정 파일
"""

# ─── 타겟 답변자 설정 ───
TARGET_ANSWERER = "새집느낌"

# ─── 구글 시트 설정 ───
GOOGLE_SHEETS_CREDENTIALS_FILE = "credentials.json"  # 서비스 계정 JSON 키 파일 경로
SPREADSHEET_NAME = "네이버 지식인 모니터링"  # 구글 시트 이름 (또는 SPREADSHEET_KEY 사용)
SPREADSHEET_KEY = ""  # 구글 시트 URL에서 /d/ 뒤의 키 (비워두면 이름으로 검색)
WORKSHEET_NAME = "Sheet1"  # 워크시트(탭) 이름

# ─── 검색 설정 ───
TOP_N_RESULTS = 2  # 검색 결과에서 확인할 상위 게시물 수 (1위, 2위)

# ─── 안티 디텍션 설정 ───
MIN_DELAY = 2  # 최소 딜레이 (초)
MAX_DELAY = 5  # 최대 딜레이 (초)
PAGE_LOAD_TIMEOUT = 30000  # 페이지 로드 타임아웃 (ms)

# ─── 브라우저 설정 ───
HEADLESS = True  # True: 백그라운드 실행, False: 브라우저 표시 (디버깅용)

# ─── User-Agent 풀 ───
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

# ─── 66개 키워드 리스트 ───
# 구글 시트에서 읽어올 수도 있고, 여기에 직접 정의할 수도 있음
# USE_SHEET_KEYWORDS = True 로 설정하면 구글 시트의 A열에서 키워드를 읽어옴
USE_SHEET_KEYWORDS = True
KEYWORDS_COLUMN = "A"  # 키워드가 있는 열
KEYWORDS_START_ROW = 2  # 키워드 시작 행 (1행은 헤더)

# 구글 시트 대신 직접 키워드를 정의할 경우 아래 리스트 사용
KEYWORDS = [
    # 예시 - 실제 키워드로 교체하세요
    # "인테리어 비용",
    # "집 리모델링",
    # ...
]
