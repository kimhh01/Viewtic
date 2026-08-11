import os
import re
import csv
import time
import json
from datetime import datetime
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# =========================
# 설정
# =========================
# 👇 JSON 파일 경로를 여기에 입력하세요 (예: "data.json" 또는 전체 경로)
INPUT_JSON_FILE = r"data\skincare_reviews_for_llm_analysis_quarterly.json"

# 크롤링 결과 저장 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_CSV = os.path.join(DATA_DIR, "reddit_crawling_result.csv")

TIME_FILTER = "year"
SORT = "relevance"        # ✅ 관련도 기반 검색

CANDIDATE_RESULTS = 40

MIN_SCORE = 50.0
MAX_POSTS_PER_KEYWORD = 8
MAX_COMMENTS_PER_POST = 60

SUBREDDITS = ["AsianBeauty", "SkincareAddiction"]  # 전체 검색하고 싶으면 [] 로

DELAY_BETWEEN_PAGES = 2.0
DELAY_BETWEEN_KEYWORDS = 4.5

# =========================
# 키워드 추출 함수 (JSON 전용으로 수정됨)
# =========================
def get_product_keywords_from_json(file_path: str) -> list[str]:
    """
    지정된 JSON 파일에서 'products' -> 'product_name'을 추출하여 리스트로 반환합니다.
    """
    if not os.path.exists(file_path):
        print(f"❌ 파일이 존재하지 않습니다: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        keywords = []
        # JSON 구조에 따라 products 키 내부 순회
        if "products" in data:
            for product in data["products"]:
                if "product_name" in product:
                    name = product["product_name"]
                    if name: # 빈 문자열 제외
                        keywords.append(name)
        else:
            print("❌ JSON 파일 내에 'products' 키가 없습니다.")
            return []

        # 중복 제거
        keywords = list(set(keywords))
        
        print(f"✅ 총 {len(keywords)}개의 제품 키워드를 JSON에서 로드했습니다.")
        return keywords
        
    except Exception as e:
        print(f"❌ 키워드 로딩 중 오류 발생: {e}")
        return []

# =========================
# 드라이버
# =========================
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # 봇 탐지 방지를 위한 User-Agent 설정
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    return driver, wait


# =========================
# URL 빌더 (old.reddit)
# =========================
def build_search_url(keyword: str, subreddit: str | None = None) -> str:
    q = quote_plus(keyword)
    if subreddit:
        return f"https://old.reddit.com/r/{subreddit}/search?q={q}&restrict_sr=on&sort={SORT}&t={TIME_FILTER}"
    return f"https://old.reddit.com/search?q={q}&sort={SORT}&t={TIME_FILTER}"


# =========================
# 관련도 점수
# =========================
def normalize(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def keyword_tokens(keyword: str) -> list[str]:
    kw = normalize(keyword)
    # 3글자 이상인 단어만 토큰으로 사용
    toks = [t for t in re.split(r"[^a-z0-9]+", kw) if len(t) >= 3]
    return toks


def relevance_score(keyword: str, title: str, snippet: str) -> float:
    kw = normalize(keyword)
    t = normalize(title)
    s = normalize(snippet)
    text = f"{t} {s}"

    score = 0.0

    # 키워드가 통째로 들어있으면 높은 점수
    if kw and kw in text:
        score += 100.0

    toks = keyword_tokens(keyword)
    if toks:
        hits_title = sum(1 for tok in set(toks) if tok in t)
        hits_text = sum(1 for tok in set(toks) if tok in text)

        score += hits_title * 20.0
        score += hits_text * 8.0

        ratio = hits_text / max(len(set(toks)), 1)
        score += ratio * 10.0

    # 광고성/공지성 글 필터링 (점수 차감)
    bad = ["giveaway", "promo", "affiliate", "coupon", "megathread", "weekly", "rules", "moderator"]
    if any(b in t for b in bad):
        score -= 50.0

    return score


# =========================
# 검색 결과 -> 후보 수집
# =========================
def collect_candidates(driver, wait, keyword: str, subreddit: str | None) -> list[dict]:
    url = build_search_url(keyword, subreddit)
    driver.get(url)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-result")))
    except TimeoutException:
        return []

    candidates = []
    results = driver.find_elements(By.CSS_SELECTOR, "div.search-result")

    for r in results[:CANDIDATE_RESULTS]:
        title = ""
        try:
            title = r.find_element(By.CSS_SELECTOR, "a.search-title").text.strip()
        except:
            continue

        snippet = ""
        try:
            snippet = r.find_element(By.CSS_SELECTOR, "div.search-result-body").text.strip()
        except:
            snippet = ""

        post_url = ""
        try:
            anchors = r.find_elements(By.CSS_SELECTOR, 'a[href*="/comments/"]')
            if anchors:
                post_url = anchors[0].get_attribute("href")
        except:
            post_url = ""

        if not post_url or "/comments/" not in post_url:
            continue

        score = relevance_score(keyword, title, snippet)

        candidates.append({
            "keyword": keyword,
            "subreddit": subreddit or "ALL",
            "post_url": post_url,
            "title": title,
            "snippet": snippet,
            "score": score
        })

    # 점수 높은 순 정렬
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # 중복 URL 제거
    seen = set()
    uniq = []
    for c in candidates:
        if c["post_url"] not in seen:
            uniq.append(c)
            seen.add(c["post_url"])
        if len(uniq) >= CANDIDATE_RESULTS:
            break

    return uniq


# =========================
# 게시글 페이지 -> 본문/댓글 + 날짜 추출
# =========================
def scrape_post_and_comments(driver, wait, post_url: str) -> dict:
    driver.get(post_url)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#siteTable")))
    except TimeoutException:
        return {"post_url": post_url, "error": "timeout"}

    # ✅ 수집시각
    collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    post_title = ""
    try:
        post_title = driver.find_element(By.CSS_SELECTOR, "#siteTable a.title").text.strip()
    except:
        pass

    post_body = ""
    try:
        post_body = driver.find_element(By.CSS_SELECTOR, "#siteTable div.expando div.md").text.strip()
    except:
        post_body = ""

    # ✅ 게시글 작성일(ISO)
    post_time_iso = ""
    for sel in ["#siteTable p.tagline time", "#siteTable time"]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            post_time_iso = el.get_attribute("datetime") or ""
            if post_time_iso:
                break
        except:
            pass

    comment_rows = []
    entries = driver.find_elements(By.CSS_SELECTOR, "div.comment div.entry")

    for entry in entries:
        if len(comment_rows) >= MAX_COMMENTS_PER_POST:
            break

        try:
            body = entry.find_element(By.CSS_SELECTOR, "div.md").text.strip()
        except:
            continue

        author = ""
        try:
            author = entry.find_element(By.CSS_SELECTOR, "a.author").text.strip()
        except:
            author = ""

        # ✅ 댓글 작성일(ISO)
        comment_time_iso = ""
        try:
            t = entry.find_element(By.CSS_SELECTOR, "p.tagline time")
            comment_time_iso = t.get_attribute("datetime") or ""
        except:
            comment_time_iso = ""

        comment_rows.append({
            "comment_author": author,
            "comment_text": body,
            "comment_time_iso": comment_time_iso
        })

    return {
        "post_url": post_url,
        "post_title": post_title,
        "post_body": post_body,
        "post_time_iso": post_time_iso,
        "collected_at": collected_at,
        "comments": comment_rows
    }


def save_csv(rows: list[dict], out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    fieldnames = [
        "keyword", "subreddit", "relevance_score",
        "post_url", "post_title", "post_body",
        "post_time_iso", "comment_time_iso", "collected_at",
        "comment_author", "comment_text"
    ]

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\n✅ 저장 완료: {out_path} (rows={len(rows)})")


# =========================
# 메인 함수
# =========================
def main(keywords=None, out_csv: str = OUT_CSV):
    # 키워드가 없으면 JSON 파일에서 로드
    if keywords is None:
        keywords = get_product_keywords_from_json(INPUT_JSON_FILE)
        
    if not keywords:
        print("❌ 검색할 키워드(제품명)가 없습니다. 프로그램을 종료합니다.")
        return

    driver, wait = setup_driver()

    all_rows = []
    try:
        for i, kw in enumerate(keywords, 1):
            print(f"\n[{i}/{len(keywords)}] keyword='{kw}'")

            scopes = SUBREDDITS if SUBREDDITS else [None]

            chosen = []
            for sub in scopes:
                cand = collect_candidates(driver, wait, kw, sub)
                chosen.extend(cand)
                time.sleep(DELAY_BETWEEN_PAGES)

            # 관련도 점수 기준 정렬 및 필터링
            chosen.sort(key=lambda x: x["score"], reverse=True)
            chosen = [c for c in chosen if c["score"] >= MIN_SCORE]
            chosen = chosen[:MAX_POSTS_PER_KEYWORD]

            print(f"  -> chosen posts (score>={MIN_SCORE}): {len(chosen)}")
            for c in chosen[:5]:
                print(f"     score={c['score']:.1f} | {c['title'][:60]}...")

            # 선택된 게시글 크롤링
            for idx, c in enumerate(chosen, 1):
                data = scrape_post_and_comments(driver, wait, c["post_url"])
                if data.get("error"):
                    continue

                # 게시글 본문만 저장 (댓글 없는 경우 대비) 또는 댓글과 함께 저장
                # 여기서는 댓글 단위로 row를 생성하되, 댓글이 없으면 본문만이라도 저장하도록 로직 구성 가능
                # 현재 로직: 댓글이 있어야 row가 생성됨. (필요 시 수정 가능)
                
                if not data["comments"]:
                     # 댓글이 없을 경우 게시글 정보만이라도 한 줄 추가
                    all_rows.append({
                        "keyword": kw,
                        "subreddit": c["subreddit"],
                        "relevance_score": c["score"],
                        "post_url": data["post_url"],
                        "post_title": data["post_title"],
                        "post_body": data["post_body"],
                        "post_time_iso": data.get("post_time_iso", ""),
                        "comment_time_iso": "",
                        "collected_at": data.get("collected_at", ""),
                        "comment_author": "",
                        "comment_text": ""
                    })
                else:
                    for cm in data["comments"]:
                        all_rows.append({
                            "keyword": kw,
                            "subreddit": c["subreddit"],
                            "relevance_score": c["score"],
                            "post_url": data["post_url"],
                            "post_title": data["post_title"],
                            "post_body": data["post_body"],
                            "post_time_iso": data.get("post_time_iso", ""),
                            "comment_time_iso": cm.get("comment_time_iso", ""),
                            "collected_at": data.get("collected_at", ""),
                            "comment_author": cm.get("comment_author", ""),
                            "comment_text": cm.get("comment_text", "")
                        })

                time.sleep(DELAY_BETWEEN_PAGES)

            time.sleep(DELAY_BETWEEN_KEYWORDS)

    finally:
        driver.quit()

    save_csv(all_rows, out_csv)
    return out_csv


if __name__ == "__main__":
    main()