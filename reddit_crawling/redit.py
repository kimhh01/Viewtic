import os
import re
import csv
import time
from datetime import datetime
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from list import get_reddit_keywords


# =========================
# 설정
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_CSV = os.path.join(DATA_DIR, "reddit_top_relevant_month.csv")

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
# 드라이버
# =========================
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
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
    toks = [t for t in re.split(r"[^a-z0-9]+", kw) if len(t) >= 3]
    return toks


def relevance_score(keyword: str, title: str, snippet: str) -> float:
    kw = normalize(keyword)
    t = normalize(title)
    s = normalize(snippet)
    text = f"{t} {s}"

    score = 0.0

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

    candidates.sort(key=lambda x: x["score"], reverse=True)

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

    # ✅ 수집시각(실행 PC 기준)
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

    # ✅ 날짜 컬럼 추가
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


# ✅ main이 OUT_CSV를 return + (선택) keywords 외부 주입 가능
def main(keywords=None, out_csv: str = OUT_CSV):
    if keywords is None:
        try:
            keywords = get_reddit_keywords(clean=True)
        except TypeError:
            keywords = get_reddit_keywords()

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

            chosen.sort(key=lambda x: x["score"], reverse=True)
            chosen = [c for c in chosen if c["score"] >= MIN_SCORE]
            chosen = chosen[:MAX_POSTS_PER_KEYWORD]

            print(f"  -> chosen posts (score>={MIN_SCORE}): {len(chosen)}")
            for c in chosen[:5]:
                print(f"     score={c['score']:.1f} | {c['title'][:60]}...")

            for idx, c in enumerate(chosen, 1):
                data = scrape_post_and_comments(driver, wait, c["post_url"])
                if data.get("error"):
                    continue

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
