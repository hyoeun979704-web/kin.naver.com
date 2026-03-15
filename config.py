"""
네이버 지식인 모니터링 봇 설정 파일
"""

# ─── 타겟 답변자 설정 ───
TARGET_ANSWERER = "새집느낌"

# ─── 구글 시트 설정 ───
GOOGLE_SHEETS_CREDENTIALS_FILE = "credentials.json"  # 서비스 계정 JSON 키 파일 경로
SPREADSHEET_KEY = "1dv40s8cfKBzSlw42-Ax74BdnVOXz_XN3iwIZK44R-8Q"
WORKSHEET_INDEX = 0  # 첫 번째 탭 (gid=0)

# ─── 시트 레이아웃 ───
# 키워드 위치
KEYWORDS_COLUMN = "A"   # 키워드 열
KEYWORDS_START_ROW = 4  # 키워드 시작 행 (1~3행은 헤더/제목)

# 결과 쓰기 열 (기존 행을 업데이트, 새 행 추가 안 함)
RANK_COL_1          = "B"  # 1위 게시물 현재 순위
LINK_COL_1          = "C"  # 1위 게시물 답변 링크
LIKES_COL_1         = "E"  # 1위 게시물 현재 따봉 갯수
NEEDED_LIKES_COL_1  = "F"  # 1위 게시물 1등에 필요한 요청 따봉 갯수
ACTUAL_LIKES_COL_1  = "G"  # 1위 게시물 실제 작업수량
RANK_COL_2          = "I"  # 2위 게시물 현재 순위
LINK_COL_2          = "J"  # 2위 게시물 답변 링크
LIKES_COL_2         = "L"  # 2위 게시물 현재 따봉 갯수
NEEDED_LIKES_COL_2  = "M"  # 2위 게시물 1등에 필요한 요청 따봉 갯수
ACTUAL_LIKES_COL_2  = "N"  # 2위 게시물 실제 작업수량

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

# ─── 키워드 소스 ───
# True: 시트 A열에서 읽기 / False: 아래 KEYWORDS 리스트 사용
USE_SHEET_KEYWORDS = True

KEYWORDS = [
    # 예시 - 실제 키워드로 교체하세요
    # "인테리어 비용",
    # "집 리모델링",
]
