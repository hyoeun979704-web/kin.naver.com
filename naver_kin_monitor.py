"""
네이버 지식인 키워드 순위 모니터링 봇
- Playwright 기반 브라우저 자동화
- Google Sheets API (gspread) 연동
- 타겟 답변자 순위 확인 및 기록
"""

import asyncio
import random
import logging
import sys
from datetime import datetime
from urllib.parse import quote_plus

import gspread
from google.oauth2.service_account import Credentials
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from config import (
    TARGET_ANSWERER,
    GOOGLE_SHEETS_CREDENTIALS_FILE,
    SPREADSHEET_NAME,
    SPREADSHEET_KEY,
    WORKSHEET_NAME,
    TOP_N_RESULTS,
    MIN_DELAY,
    MAX_DELAY,
    PAGE_LOAD_TIMEOUT,
    HEADLESS,
    USER_AGENTS,
    USE_SHEET_KEYWORDS,
    KEYWORDS_COLUMN,
    KEYWORDS_START_ROW,
    KEYWORDS,
)

# ─── 로깅 설정 ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Google Sheets 연동
# ═══════════════════════════════════════════════════════════════

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_google_sheet():
    """구글 시트 워크시트 객체를 반환합니다."""
    creds = Credentials.from_service_account_file(
        GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)

    if SPREADSHEET_KEY:
        spreadsheet = client.open_by_key(SPREADSHEET_KEY)
    else:
        spreadsheet = client.open(SPREADSHEET_NAME)

    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    logger.info(f"구글 시트 연결 완료: {spreadsheet.title} / {worksheet.title}")
    return worksheet


def load_keywords_from_sheet(worksheet):
    """구글 시트의 지정 열에서 키워드 목록을 읽어옵니다."""
    col_values = worksheet.col_values(
        ord(KEYWORDS_COLUMN.upper()) - ord("A") + 1
    )
    # 헤더 행 이후의 값만 사용하고 빈 문자열 제외
    keywords = [
        kw.strip()
        for kw in col_values[KEYWORDS_START_ROW - 1 :]
        if kw.strip()
    ]
    logger.info(f"시트에서 {len(keywords)}개 키워드 로드 완료")
    return keywords


def write_result_to_sheet(worksheet, row_data):
    """결과를 구글 시트의 다음 빈 행에 기록합니다.

    row_data 형식:
    [날짜, 키워드, 1위질문_순위, 1위질문_링크, 2위질문_순위, 2위질문_링크, 비고]
    """
    worksheet.append_row(row_data, value_input_option="USER_ENTERED")
    logger.info(f"시트 기록 완료: {row_data[1]} (키워드)")


# ═══════════════════════════════════════════════════════════════
# 안티 디텍션 유틸리티
# ═══════════════════════════════════════════════════════════════


async def random_delay(min_sec=None, max_sec=None):
    """랜덤 딜레이를 적용합니다."""
    min_s = min_sec or MIN_DELAY
    max_s = max_sec or MAX_DELAY
    delay = random.uniform(min_s, max_s)
    logger.debug(f"딜레이: {delay:.1f}초")
    await asyncio.sleep(delay)


def get_random_user_agent():
    """랜덤 User-Agent를 반환합니다."""
    return random.choice(USER_AGENTS)


# ═══════════════════════════════════════════════════════════════
# 네이버 지식인 크롤링 로직
# ═══════════════════════════════════════════════════════════════


async def search_naver_kin(page, keyword):
    """네이버 지식인에서 키워드를 검색하고 상위 N개 질문 링크를 반환합니다.

    Returns:
        list[dict]: [{"rank": 1, "url": "...", "title": "..."}, ...]
    """
    encoded_keyword = quote_plus(keyword)
    search_url = (
        f"https://kin.naver.com/search/list.naver"
        f"?query={encoded_keyword}&section=qna"
    )

    logger.info(f"검색 중: '{keyword}'")
    await page.goto(search_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
    await random_delay()

    # 검색 결과 목록에서 상위 질문 링크 추출
    results = []
    # 지식인 검색 결과는 .basic1 > li 형태로 나열됨
    search_items = await page.query_selector_all("ul.basic1 > li")

    if not search_items:
        # 대체 셀렉터 시도 (네이버 UI 변경 대응)
        search_items = await page.query_selector_all(".search_list > li")

    if not search_items:
        search_items = await page.query_selector_all("[class*='list'] > li")

    for i, item in enumerate(search_items[:TOP_N_RESULTS]):
        try:
            link_el = await item.query_selector("a[href*='kin.naver.com/qna/detail']")
            if not link_el:
                link_el = await item.query_selector("a._nclicks")
            if not link_el:
                link_el = await item.query_selector("a")

            if link_el:
                href = await link_el.get_attribute("href")
                title = (await link_el.inner_text()).strip()
                if href:
                    # 상대 경로 처리
                    if href.startswith("/"):
                        href = "https://kin.naver.com" + href
                    results.append({
                        "rank": i + 1,
                        "url": href,
                        "title": title[:50],
                    })
        except Exception as e:
            logger.warning(f"검색 결과 {i+1}번째 항목 파싱 실패: {e}")

    logger.info(f"'{keyword}' 검색 결과 {len(results)}개 추출")
    return results


async def check_answerer_rank(page, question_url, target_name):
    """질문 페이지에 접속하여 타겟 답변자의 순위를 확인합니다.

    '채택 답변'이 있으면 그것이 1위로 고정됩니다.
    '더보기' 버튼이 있으면 클릭하여 전체 답변을 확인합니다.

    Returns:
        dict: {
            "rank": int or None,  # 타겟의 순위 (없으면 None)
            "is_top1": bool,      # 1위 여부
            "total_answers": int,  # 전체 답변 수
            "top1_answerer": str,  # 1위 답변자 이름
        }
    """
    logger.info(f"질문 페이지 접속: {question_url}")
    await page.goto(question_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
    await random_delay()

    # ─── '더보기' 버튼 처리 (답변이 많을 경우) ───
    more_clicked = 0
    while True:
        try:
            more_btn = await page.query_selector(
                "a.answer_more, button.answer_more, "
                "[class*='more_answer'], a._moreBtn"
            )
            if more_btn and await more_btn.is_visible():
                await more_btn.click()
                more_clicked += 1
                await random_delay(1, 2)
                if more_clicked > 10:  # 안전장치
                    break
            else:
                break
        except Exception:
            break

    if more_clicked:
        logger.info(f"'더보기' 버튼 {more_clicked}회 클릭")

    # ─── 답변 목록 파싱 ───
    # 네이버 지식인 답변 구조:
    # 1) 채택 답변 (class에 'adopted' 포함) — 항상 최상단
    # 2) 일반 답변 (순서대로 나열)
    answer_items = await page.query_selector_all(
        ".answer-content__list > li, "
        "div.answer_area, "
        "[class*='answerArea'], "
        ".c-heading-answer__content, "
        "div[class*='answer']"
    )

    # 더 구체적인 셀렉터로 재시도
    if not answer_items:
        answer_items = await page.query_selector_all(
            "#answerArea div.se_component_wrap, "
            ".answer_component"
        )

    answerer_list = []

    for item in answer_items:
        try:
            # 답변자 이름 추출 (여러 셀렉터 시도)
            name_el = await item.query_selector(
                ".answer_nickname, "
                ".c-userinfo__name, "
                "[class*='nickname'], "
                "[class*='userName'], "
                ".profile_info a, "
                ".user_info .name, "
                "a[class*='user']"
            )
            if name_el:
                name = (await name_el.inner_text()).strip()
                if name:
                    answerer_list.append(name)
        except Exception:
            continue

    # 중복 제거하면서 순서 유지 (같은 사람이 여러 번 잡힐 수 있음)
    seen = set()
    unique_answerers = []
    for name in answerer_list:
        if name not in seen:
            seen.add(name)
            unique_answerers.append(name)

    total = len(unique_answerers)
    top1 = unique_answerers[0] if unique_answerers else "확인불가"

    # 타겟 답변자 순위 찾기
    target_rank = None
    for idx, name in enumerate(unique_answerers):
        if target_name in name:
            target_rank = idx + 1
            break

    result = {
        "rank": target_rank,
        "is_top1": target_rank == 1,
        "total_answers": total,
        "top1_answerer": top1,
    }

    logger.info(
        f"답변 분석 완료 - 총 {total}개 답변, "
        f"1위: {top1}, "
        f"'{target_name}' 순위: {target_rank or '없음'}"
    )
    return result


# ═══════════════════════════════════════════════════════════════
# 메인 실행 로직
# ═══════════════════════════════════════════════════════════════


async def process_keyword(page, keyword):
    """하나의 키워드에 대한 전체 처리 흐름을 실행합니다.

    Returns:
        dict: {
            "keyword": str,
            "date": str,
            "results": list[dict],  # [{"rank_text": ..., "url": ...}, ...]
            "note": str,
        }
    """
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1) 키워드 검색
    search_results = await search_naver_kin(page, keyword)

    if not search_results:
        logger.warning(f"'{keyword}' 검색 결과 없음 — 스킵")
        return {
            "keyword": keyword,
            "date": today,
            "results": [
                {"rank_text": "검색결과없음", "url": ""},
                {"rank_text": "검색결과없음", "url": ""},
            ],
            "note": "검색 결과를 찾을 수 없음",
        }

    # 2) 각 상위 게시물 분석
    result_items = []
    should_record = False

    for sr in search_results:
        rank_label = f"{sr['rank']}위 게시물"
        url = sr["url"]
        await random_delay()

        try:
            rank_info = await check_answerer_rank(page, url, TARGET_ANSWERER)

            if rank_info["is_top1"]:
                rank_text = f"1위 ('{TARGET_ANSWERER}' 최상단)"
                logger.info(f"[{rank_label}] '{TARGET_ANSWERER}'이(가) 1위 — 스킵")
            else:
                should_record = True
                if rank_info["rank"]:
                    rank_text = f"{rank_info['rank']}위 (1위: {rank_info['top1_answerer']})"
                else:
                    rank_text = f"순위권 밖 (1위: {rank_info['top1_answerer']}, 총 {rank_info['total_answers']}개 답변)"
                logger.info(f"[{rank_label}] '{TARGET_ANSWERER}' → {rank_text}")

        except PlaywrightTimeout:
            logger.error(f"[{rank_label}] 페이지 로드 타임아웃: {url}")
            rank_text = "타임아웃"
            should_record = True
        except Exception as e:
            logger.error(f"[{rank_label}] 분석 실패: {e}")
            rank_text = f"오류: {str(e)[:30]}"
            should_record = True

        result_items.append({"rank_text": rank_text, "url": url})

    # 부족한 결과 패딩
    while len(result_items) < TOP_N_RESULTS:
        result_items.append({"rank_text": "결과없음", "url": ""})

    note = ""
    if not should_record:
        note = f"모든 게시물에서 '{TARGET_ANSWERER}' 1위"

    return {
        "keyword": keyword,
        "date": today,
        "results": result_items,
        "note": note,
    }


def deduplicate_and_write(all_results, worksheet):
    """전체 결과에서 중복 링크를 찾아 '중복' 표시 후 시트에 기록합니다.

    동일한 URL이 여러 키워드에서 등장할 경우,
    가장 처음 등장한 것만 원래 순위를 유지하고
    이후 등장은 순위란에 '중복'으로 표시합니다.
    """
    seen_urls = set()  # 전체 키워드에 걸쳐 이미 등장한 URL 추적
    duplicate_count = 0

    for entry in all_results:
        row = [entry["date"], entry["keyword"]]

        for item in entry["results"]:
            url = item["url"]
            rank_text = item["rank_text"]

            if url and url in seen_urls:
                # 이미 다른 키워드에서 등장한 링크 → 중복 표시
                row.extend(["중복", url])
                duplicate_count += 1
                logger.info(
                    f"[중복 감지] '{entry['keyword']}' — {url}"
                )
            else:
                row.extend([rank_text, url])
                if url:
                    seen_urls.add(url)

        row.append(entry["note"])
        write_result_to_sheet(worksheet, row)

    logger.info(f"중복 링크 총 {duplicate_count}건 감지 및 표시 완료")


async def main():
    """메인 실행 함수"""
    logger.info("=" * 60)
    logger.info("네이버 지식인 모니터링 봇 시작")
    logger.info(f"타겟 답변자: {TARGET_ANSWERER}")
    logger.info("=" * 60)

    # 1) 구글 시트 연결
    try:
        worksheet = get_google_sheet()
    except Exception as e:
        logger.error(f"구글 시트 연결 실패: {e}")
        logger.error("credentials.json 파일과 시트 공유 설정을 확인하세요.")
        sys.exit(1)

    # 2) 키워드 로드
    if USE_SHEET_KEYWORDS:
        keywords = load_keywords_from_sheet(worksheet)
    else:
        keywords = KEYWORDS

    if not keywords:
        logger.error("키워드가 없습니다. config.py를 확인하세요.")
        sys.exit(1)

    logger.info(f"총 {len(keywords)}개 키워드 처리 예정")

    # 3) 시트 헤더 확인/작성
    existing_headers = worksheet.row_values(1)
    expected_headers = [
        "날짜", "키워드",
        "1위 게시물 순위", "1위 게시물 링크",
        "2위 게시물 순위", "2위 게시물 링크",
        "비고",
    ]
    if not existing_headers or existing_headers[0] != expected_headers[0]:
        worksheet.insert_row(expected_headers, 1)
        logger.info("시트 헤더 작성 완료")

    # 4) Playwright 브라우저 시작
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent=get_random_user_agent(),
            viewport={"width": 1366, "height": 768},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
        )

        # navigator.webdriver 감지 우회
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)

        page = await context.new_page()

        # 5) 키워드별 처리 — 결과를 메모리에 수집
        all_results = []
        success_count = 0
        fail_count = 0

        for i, keyword in enumerate(keywords, 1):
            logger.info(f"\n{'─' * 40}")
            logger.info(f"[{i}/{len(keywords)}] 키워드: '{keyword}'")
            logger.info(f"{'─' * 40}")

            try:
                result = await process_keyword(page, keyword)
                all_results.append(result)
                success_count += 1
            except Exception as e:
                logger.error(f"키워드 '{keyword}' 처리 중 오류: {e}")
                fail_count += 1

            # 키워드 간 딜레이 (봇 탐지 방지)
            if i < len(keywords):
                delay = random.uniform(MIN_DELAY + 1, MAX_DELAY + 2)
                logger.info(f"다음 키워드까지 {delay:.1f}초 대기...")
                await asyncio.sleep(delay)

            # 10개 키워드마다 User-Agent 변경
            if i % 10 == 0:
                new_ua = get_random_user_agent()
                logger.info(f"User-Agent 변경: ...{new_ua[-30:]}")
                await context.close()
                context = await browser.new_context(
                    user_agent=new_ua,
                    viewport={"width": 1366, "height": 768},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                    });
                """)
                page = await context.new_page()

        await browser.close()

    # 6) 전체 결과에서 중복 링크 처리 후 시트에 일괄 기록
    logger.info("\n" + "─" * 40)
    logger.info("전체 키워드 탐색 완료 — 중복 링크 검사 및 시트 기록 시작")
    logger.info("─" * 40)
    deduplicate_and_write(all_results, worksheet)

    # 7) 완료 리포트
    logger.info("\n" + "=" * 60)
    logger.info("모니터링 완료!")
    logger.info(f"성공: {success_count}개 / 실패: {fail_count}개 / 전체: {len(keywords)}개")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
