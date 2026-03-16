"""
네이버 지식인 키워드 순위 모니터링 봇
- Playwright 기반 브라우저 자동화
- Google Sheets API (gspread) 연동
- 타겟 답변자 순위 확인 및 기록
"""

import asyncio
import base64
import json
import os
import random
import logging
import re
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# 스크립트 파일 기준 디렉토리 (실행 위치와 무관하게 동작)
BASE_DIR = Path(__file__).resolve().parent

from config import (
    TARGET_ANSWERER,
    GOOGLE_SHEETS_CREDENTIALS_FILE,
    SPREADSHEET_KEY,
    WORKSHEET_INDEX,
    TOP_N_RESULTS,
    MIN_DELAY,
    MAX_DELAY,
    PAGE_LOAD_TIMEOUT,
    HEADLESS,
    USER_AGENTS,
    USE_SHEET_KEYWORDS,
    KEYWORDS_COLUMN,
    KEYWORDS_START_ROW,
    RANK_COL_1,
    LINK_COL_1,
    LIKES_COL_1,
    NEEDED_LIKES_COL_1,
    ACTUAL_LIKES_COL_1,
    RANK_COL_2,
    LINK_COL_2,
    LIKES_COL_2,
    NEEDED_LIKES_COL_2,
    ACTUAL_LIKES_COL_2,
    KEYWORDS,
)

# ─── 한국 시간(KST) 기준 오전/오후 판단 ───
KST = timezone(timedelta(hours=9))


def is_afternoon():
    """한국 시간 12시 이후이면 오후(True)를 반환합니다."""
    return datetime.now(KST).hour >= 12

# ─── 로깅 설정 ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "monitor.log", encoding="utf-8"),
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


def col_letter_to_index(letter):
    """열 문자를 1-based 인덱스로 변환 (A→1, B→2, ...)"""
    return ord(letter.upper()) - ord("A") + 1


def _load_credentials():
    """구글 서비스 계정 인증 정보를 로드합니다.

    우선순위:
      1. 환경변수 GOOGLE_CREDENTIALS_JSON (JSON 문자열)
      2. 환경변수 GOOGLE_CREDENTIALS_BASE64 (Base64 인코딩)
      3. credentials.json 파일
    """
    env_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if env_json:
        info = json.loads(env_json)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    env_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")
    if env_b64:
        info = json.loads(base64.b64decode(env_b64))
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    creds_path = BASE_DIR / GOOGLE_SHEETS_CREDENTIALS_FILE
    if creds_path.exists():
        return Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)

    logger.error(
        "인증 정보를 찾을 수 없습니다. 다음 중 하나를 설정하세요:\n"
        "  1. 환경변수 GOOGLE_CREDENTIALS_JSON (JSON 문자열)\n"
        "  2. 환경변수 GOOGLE_CREDENTIALS_BASE64 (Base64 인코딩)\n"
        "  3. credentials.json 파일을 프로젝트 폴더에 배치"
    )
    sys.exit(1)


def get_google_sheet():
    """구글 시트 워크시트 객체를 반환합니다."""
    creds = _load_credentials()
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_KEY)
    worksheet = spreadsheet.get_worksheet(WORKSHEET_INDEX)
    logger.info(f"구글 시트 연결 완료: {spreadsheet.title} / {worksheet.title}")
    return worksheet


def load_keywords_from_sheet(worksheet):
    """구글 시트 A열에서 키워드와 행 번호를 함께 반환합니다.

    Returns:
        list[tuple]: [(row_number, keyword), ...]
    """
    col_idx = col_letter_to_index(KEYWORDS_COLUMN)
    col_values = worksheet.col_values(col_idx)

    entries = []
    for i, val in enumerate(col_values[KEYWORDS_START_ROW - 1:], start=KEYWORDS_START_ROW):
        kw = val.strip()
        if kw:
            entries.append((i, kw))

    logger.info(f"시트에서 {len(entries)}개 키워드 로드 완료")
    return entries


def flush_to_sheet(worksheet, all_results, afternoon=False):
    """전체 결과에서 중복 URL을 처리하고 시트의 해당 행 셀을 일괄 업데이트합니다.

    오전 실행: 요청 따봉 갯수(F/M열)에 기록
    오후 실행: 실제 작업수량(G/N열)에 기록

    쓰기 대상 열:
      B(RANK_COL_1): 1위 게시물 현재 순위
      C(LINK_COL_1): 1위 게시물 답변 링크
      I(RANK_COL_2): 2위 게시물 현재 순위
      J(LINK_COL_2): 2위 게시물 답변 링크
    """
    seen_doc_ids = set()
    duplicate_count = 0

    # gspread batch_update 형식: [{"range": "B4", "values": [["값"]]}, ...]
    updates = []

    def extract_doc_id(url):
        """URL에서 docId를 추출합니다."""
        match = re.search(r'docId=(\d+)', url)
        return match.group(1) if match else url

    for entry in all_results:
        row = entry["row"]
        results = entry["results"]  # 최대 2개: [1위 게시물, 2위 게시물]

        col_pairs = [
            (RANK_COL_1, LINK_COL_1, LIKES_COL_1, NEEDED_LIKES_COL_1, ACTUAL_LIKES_COL_1),
            (RANK_COL_2, LINK_COL_2, LIKES_COL_2, NEEDED_LIKES_COL_2, ACTUAL_LIKES_COL_2),
        ]

        for idx, (rank_col, link_col, likes_col, needed_col, actual_col) in enumerate(col_pairs):
            if idx >= len(results):
                break

            item = results[idx]
            url = item["url"]
            rank_text = item["rank_text"]
            likes = item["likes"]
            needed_likes = item.get("needed_likes")

            # 중복 링크 처리 (docId 기준)
            doc_id = extract_doc_id(url) if url else None
            if doc_id and doc_id in seen_doc_ids:
                rank_text = "중복"
                duplicate_count += 1
                logger.info(f"[중복 감지] '{entry['keyword']}' {idx+1}위 게시물 — docId={doc_id}")
            elif doc_id:
                seen_doc_ids.add(doc_id)

            updates.append({"range": f"{rank_col}{row}", "values": [[rank_text]]})

            if afternoon:
                # 오후: 순위 + 실제 작업수량(현재 따봉 갯수)만 기록
                updates.append({
                    "range": f"{actual_col}{row}",
                    "values": [[likes if likes is not None else ""]],
                })
            else:
                # 오전: 순위 + 링크 + 따봉 갯수 + 요청 갯수
                updates.append({"range": f"{link_col}{row}", "values": [[url]]})
                if likes is not None:
                    updates.append({"range": f"{likes_col}{row}", "values": [[likes]]})
                updates.append({
                    "range": f"{needed_col}{row}",
                    "values": [[needed_likes if needed_likes is not None else ""]],
                })

    if updates:
        worksheet.batch_update(updates, value_input_option="USER_ENTERED")

    logger.info(
        f"시트 업데이트 완료 — {len(all_results)}개 키워드, "
        f"중복 {duplicate_count}건"
    )


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

    results = []
    search_items = await page.query_selector_all("ul.basic1 > li")

    if not search_items:
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
            "rank": int or None,
            "is_top1": bool,
            "total_answers": int,
            "top1_answerer": str,
            "target_likes": int or None,  # 타겟 답변자의 따봉 갯수
        }
    """
    logger.info(f"질문 페이지 접속: {question_url}")
    await page.goto(question_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
    await random_delay()

    # ─── '더보기' 버튼 처리 ───
    more_clicked = 0
    while True:
        try:
            more_btn = await page.query_selector(
                "button.endAnswerMoreButton, #nextPageButton, "
                "a.answer_more, button.answer_more, "
                "[class*='more_answer'], a._moreBtn"
            )
            if more_btn and await more_btn.is_visible():
                await more_btn.click()
                more_clicked += 1
                await random_delay(1, 2)
                if more_clicked > 10:
                    break
            else:
                break
        except Exception:
            break

    if more_clicked:
        logger.info(f"'더보기' 버튼 {more_clicked}회 클릭")

    # ─── 답변 목록 파싱 ───
    answer_items = await page.query_selector_all("div._contentBox")

    if not answer_items:
        answer_items = await page.query_selector_all(
            "div.contentBox, "
            ".answer-content__list > li, "
            "div.answer_area"
        )

    # 답변자별 (이름, 따봉수, 답변번호) 수집
    answerer_data = []  # [(name, likes, answer_no), ...]
    for item in answer_items:
        try:
            # 답변 번호 추출 — id="answer_13" → "13"
            answer_no = None
            answer_el = await item.query_selector("[id^='answer_']")
            if answer_el:
                answer_id = await answer_el.get_attribute("id")
                if answer_id and "_" in answer_id:
                    answer_no = answer_id.split("_", 1)[1]

            # 답변자 이름 — career_list span에서 해시태그 파싱
            name = None

            # 방법1: career_list span에서 "#닉네임" 추출
            career_el = await item.query_selector(".career_list span")
            if career_el:
                career_text = (await career_el.inner_text()).strip()
                # "#16600240 #입주청소 #새집느낌" → 마지막 해시태그가 닉네임
                parts = [p.strip() for p in career_text.split("#") if p.strip()]
                if parts:
                    name = parts[-1]

            # 방법2: card_info 내 닉네임 요소
            if not name:
                for sel in [
                    ".card_info .nickname",
                    ".card_info .name",
                    ".nick",
                    ".name_area .name",
                    ".profileCard .nickname",
                    "[class*='nickname']",
                    "[class*='userName']",
                ]:
                    name_el = await item.query_selector(sel)
                    if name_el:
                        name = (await name_el.inner_text()).strip()
                        if name:
                            break

            if not name:
                continue

            # 따봉(추천) 갯수 — 여러 셀렉터 시도
            likes = None
            for sel in [
                ".countWrap ._count",
                "span._count_rollup_now",
                "span._count",
                ".u_cnt_num",
                "[class*='sympathy'] [class*='count']",
                "[class*='like'] [class*='count']",
                ".btn_sympathy .count",
            ]:
                likes_el = await item.query_selector(sel)
                if likes_el:
                    likes_text = (await likes_el.inner_text()).strip().replace(",", "")
                    if likes_text.isdigit():
                        likes = int(likes_text)
                        break

            answerer_data.append((name, likes, answer_no))
            logger.debug(f"  답변자 발견: {name}, 따봉: {likes}, answerNo: {answer_no}")
        except Exception:
            continue

    # 중복 이름 제거 (순서 유지, 첫 등장 기준)
    seen = set()
    unique_data = []
    for name, likes, answer_no in answerer_data:
        if name not in seen:
            seen.add(name)
            unique_data.append((name, likes, answer_no))

    total = len(unique_data)
    top1 = unique_data[0][0] if unique_data else "확인불가"
    top1_likes = unique_data[0][1] if unique_data else None

    target_rank = None
    target_likes = None
    target_answer_no = None
    for idx, (name, likes, answer_no) in enumerate(unique_data):
        if target_name in name:
            target_rank = idx + 1
            target_likes = likes
            target_answer_no = answer_no
            break

    result = {
        "rank": target_rank,
        "is_top1": target_rank == 1,
        "total_answers": total,
        "top1_answerer": top1,
        "top1_likes": top1_likes,
        "target_likes": target_likes,
        "target_answer_no": target_answer_no,
    }

    logger.info(
        f"답변 분석 완료 - 총 {total}개, "
        f"1위: {top1}, "
        f"'{target_name}' 순위: {target_rank or '없음'}, "
        f"따봉: {target_likes if target_likes is not None else '없음'}"
    )
    return result


# ═══════════════════════════════════════════════════════════════
# 메인 실행 로직
# ═══════════════════════════════════════════════════════════════


def calc_needed_likes(top1_likes, target_likes):
    """1위가 되기 위해 필요한 요청 따봉 갯수를 계산합니다.

    - 1위 따봉 수를 넘기 위해 필요한 차이를 구합니다.
    - 최소 10개, 5개 단위로 올림합니다.

    Returns:
        int or None: 필요한 따봉 갯수 (이미 1위이거나 데이터 없으면 None)
    """
    if top1_likes is None or target_likes is None:
        return None
    raw = top1_likes - target_likes + 1
    if raw <= 0:
        return None  # 이미 1위 따봉 수 이상
    # 5 단위 올림, 최소 10
    rounded = ((raw + 4) // 5) * 5
    return max(rounded, 10)


async def process_keyword(page, row_number, keyword):
    """하나의 키워드에 대한 전체 처리 흐름을 실행합니다.

    Returns:
        dict: {
            "row": int,           # 시트 행 번호
            "keyword": str,
            "results": list[dict],  # [{"rank_text": ..., "url": ...}, ...]
        }
    """
    search_results = await search_naver_kin(page, keyword)

    if not search_results:
        logger.warning(f"'{keyword}' 검색 결과 없음")
        return {
            "row": row_number,
            "keyword": keyword,
            "results": [
                {"rank_text": "검색결과없음", "url": "", "likes": None, "needed_likes": None},
                {"rank_text": "검색결과없음", "url": "", "likes": None, "needed_likes": None},
            ],
        }

    result_items = []

    for sr in search_results:
        rank_label = f"{sr['rank']}위 게시물"
        url = sr["url"]
        await random_delay()

        try:
            rank_info = await check_answerer_rank(page, url, TARGET_ANSWERER)

            if rank_info["is_top1"]:
                rank_text = "1"
                logger.info(f"[{rank_label}] '{TARGET_ANSWERER}' 1위")
            else:
                if rank_info["rank"]:
                    rank_text = str(rank_info["rank"])
                else:
                    rank_text = f"없음(1위:{rank_info['top1_answerer']})"
                logger.info(f"[{rank_label}] '{TARGET_ANSWERER}' → {rank_text}위")

            likes = rank_info["target_likes"]

            # 1위가 되기 위해 필요한 따봉 갯수 계산
            needed_likes = None
            if not rank_info["is_top1"] and rank_info["rank"]:
                needed_likes = calc_needed_likes(
                    rank_info["top1_likes"], rank_info["target_likes"]
                )

            # URL에 answerNo 파라미터 추가
            answer_no = rank_info.get("target_answer_no")
            if answer_no:
                url = f"{url}&answerNo={answer_no}"

        except PlaywrightTimeout:
            logger.error(f"[{rank_label}] 타임아웃: {url}")
            rank_text = "타임아웃"
            likes = None
            needed_likes = None
        except Exception as e:
            logger.error(f"[{rank_label}] 오류: {e}")
            rank_text = "오류"
            likes = None
            needed_likes = None

        result_items.append({
            "rank_text": rank_text,
            "url": url,
            "likes": likes,
            "needed_likes": needed_likes,
        })

    # 결과가 TOP_N_RESULTS보다 적을 경우 패딩
    while len(result_items) < TOP_N_RESULTS:
        result_items.append({"rank_text": "", "url": "", "likes": None, "needed_likes": None})

    return {
        "row": row_number,
        "keyword": keyword,
        "results": result_items,
    }


async def main():
    """메인 실행 함수"""
    afternoon = is_afternoon()
    mode_label = "오후 (실제 작업수량 기록)" if afternoon else "오전 (요청 갯수 기록)"
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    logger.info("=" * 60)
    logger.info("네이버 지식인 모니터링 봇 시작")
    logger.info(f"실행 시각: {now_kst} (KST)")
    logger.info(f"실행 모드: {mode_label}")
    logger.info(f"타겟 답변자: {TARGET_ANSWERER}")
    logger.info("=" * 60)

    # 1) 구글 시트 연결
    try:
        worksheet = get_google_sheet()
    except Exception as e:
        logger.error(f"구글 시트 연결 실패: {e}")
        logger.error("credentials.json 파일과 시트 공유 설정을 확인하세요.")
        sys.exit(1)

    # 2) 키워드 로드 (행 번호 포함)
    if USE_SHEET_KEYWORDS:
        keyword_entries = load_keywords_from_sheet(worksheet)
    else:
        keyword_entries = [
            (KEYWORDS_START_ROW + i, kw) for i, kw in enumerate(KEYWORDS)
        ]

    if not keyword_entries:
        logger.error("키워드가 없습니다. config.py 또는 시트를 확인하세요.")
        sys.exit(1)

    logger.info(f"총 {len(keyword_entries)}개 키워드 처리 예정")

    # 3) Playwright 브라우저 시작
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

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)

        page = await context.new_page()

        # 4) 키워드별 처리 — 결과를 메모리에 수집
        all_results = []
        success_count = 0
        fail_count = 0

        for i, (row_number, keyword) in enumerate(keyword_entries, 1):
            logger.info(f"\n{'─' * 40}")
            logger.info(f"[{i}/{len(keyword_entries)}] 행{row_number} '{keyword}'")
            logger.info(f"{'─' * 40}")

            try:
                result = await process_keyword(page, row_number, keyword)
                all_results.append(result)
                success_count += 1
            except Exception as e:
                logger.error(f"'{keyword}' 처리 중 오류: {e}")
                fail_count += 1

            # 키워드 간 딜레이
            if i < len(keyword_entries):
                delay = random.uniform(MIN_DELAY + 1, MAX_DELAY + 2)
                logger.info(f"다음 키워드까지 {delay:.1f}초 대기...")
                await asyncio.sleep(delay)

            # 10개마다 User-Agent 교체
            if i % 10 == 0:
                new_ua = get_random_user_agent()
                logger.info(f"User-Agent 변경")
                await context.close()
                context = await browser.new_context(
                    user_agent=new_ua,
                    viewport={"width": 1366, "height": 768},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => false });
                """)
                page = await context.new_page()

        await browser.close()

    # 5) 중복 처리 후 시트에 일괄 업데이트
    logger.info("\n" + "─" * 40)
    logger.info("탐색 완료 — 중복 검사 및 시트 기록 시작")
    logger.info("─" * 40)
    flush_to_sheet(worksheet, all_results, afternoon=afternoon)

    # 6) 완료 리포트
    logger.info("\n" + "=" * 60)
    logger.info("모니터링 완료!")
    logger.info(f"성공: {success_count} / 실패: {fail_count} / 전체: {len(keyword_entries)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
