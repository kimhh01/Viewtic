# 올리브영 글로벌 사이트 크롤링 코드 

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import os
from datetime import datetime

# ========================================
# 설정 및 초기화
# ========================================
BASE_URL = "https://global.oliveyoung.com/display/page/best-seller?target=pillsTab1Nav1"
MAX_PRODUCTS = 100
MAX_MORE_CLICKS = 10
OUTPUT_DIR = "data"

# 수집 메타데이터
COLLECTION_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
COLLECTION_BATCH = f"{datetime.now().year}Q{(datetime.now().month - 1) // 3 + 1}"

# 카테고리 매핑
CATEGORY_MAP = {
    "1000000015": "Essence & Serum",
    "1000000016": "Cream",
    "1000000021": "Cleansing Foams",
    "1000000022": "Cleansing Balms & Oils",
    "1000000017": "Face Mist",
    "1000000026": "Exfoliators",
    "1000000261": "Acne & Blemish Treatments"
}

# ========================================
# 유틸리티 함수
# ========================================
def get_star_score(star_rating_div):
    """별점 계산 (filled 아이콘 개수 / 2)"""
    try:
        filled_stars = star_rating_div.find_elements(By.CSS_SELECTOR, ".icon-star.filled")
        return len(filled_stars) / 2
    except:
        return 0

def parse_review_date(date_str):
    """날짜 문자열을 표준 형식으로 변환 (YYYY/MM/DD → YYYY-MM-DD)"""
    try:
        date_str = date_str.strip()
        if not date_str:
            return {"review_date": None, "review_month": None}
        
        parsed_date = datetime.strptime(date_str, "%Y/%m/%d")
        return {
            "review_date": parsed_date.strftime("%Y-%m-%d"),
            "review_month": parsed_date.strftime("%Y-%m")
        }
    except:
        return {"review_date": None, "review_month": None}

def extract_review_date(review_card):
    """리뷰 카드에서 작성 날짜 추출 (4가지 방법 시도)"""
    date_text = None
    
    # 방법 1: CSS 선택자
    try:
        date_span = review_card.find_element(By.CSS_SELECTOR, 'span.review-write-info-date')
        date_text = date_span.text.strip()
    except:
        pass
    
    # 방법 2: 클래스 이름
    if not date_text:
        try:
            date_spans = review_card.find_elements(By.CLASS_NAME, 'review-write-info-date')
            if date_spans:
                date_text = date_spans[0].text.strip()
        except:
            pass
    
    # 방법 3: XPath
    if not date_text:
        try:
            date_spans = review_card.find_elements(By.XPATH, './/span[@class="review-write-info-date notranslate"]')
            if date_spans:
                date_text = date_spans[0].text.strip()
        except:
            pass
    
    # 방법 4: 패턴 매칭 (YYYY/MM/DD 형식)
    if not date_text:
        try:
            all_spans = review_card.find_elements(By.TAG_NAME, 'span')
            for span in all_spans:
                text = span.text.strip()
                if text and '/' in text and len(text) == 10:
                    parts = text.split('/')
                    if len(parts) == 3 and parts[0].isdigit() and len(parts[0]) == 4:
                        date_text = text
                        break
        except:
            pass
    
    return parse_review_date(date_text) if date_text else {"review_date": None, "review_month": None}

def parse_skin_info(review_card):
    """피부 타입 및 고민 정보 추출 (XPath 기반)"""
    skin_type = None
    skin_concerns = []
    
    try:
        # Skin Type 추출
        skin_type_elements = review_card.find_elements(
            By.XPATH, 
            './/div[@class="user-skin-data"]//dl[dt[text()="Skin Type"]]/div/dd'
        )
        if skin_type_elements:
            skin_type = skin_type_elements[0].text.strip()
        
        # Skin Concern 추출
        skin_concern_elements = review_card.find_elements(
            By.XPATH,
            './/div[@class="user-skin-data"]//dl[dt[text()="Skin Concern"]]/div/dd'
        )
        if skin_concern_elements:
            skin_concerns = [elem.text.strip() for elem in skin_concern_elements if elem.text.strip()]
    except:
        pass
    
    return {
        "skin_type": skin_type,
        "skin_concerns": ", ".join(skin_concerns) if skin_concerns else None
    }

# ========================================
# 드라이버 설정
# ========================================
def setup_driver():
    """Chrome 드라이버 초기화"""
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)
    return driver, WebDriverWait(driver, 20)

# ========================================
# 크롤링 함수
# ========================================
def navigate_to_skincare(driver, wait):
    """Skincare 카테고리로 이동"""
    print("📍 베스트셀러 페이지 접속")
    driver.get(BASE_URL)
    time.sleep(5)
    
    print("📍 Skincare 탭 클릭 시도")
    try:
        skincare_tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-ctgr-no="1000000008"]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", skincare_tab)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", skincare_tab)
        print("✅ Skincare 탭 클릭 성공")
    except TimeoutException:
        skincare_tabs = driver.find_elements(By.XPATH, "//a[contains(text(), 'Skincare') or contains(text(), 'skincare')]")
        if skincare_tabs:
            driver.execute_script("arguments[0].scrollIntoView(true);", skincare_tabs[0])
            time.sleep(1)
            driver.execute_script("arguments[0].click();", skincare_tabs[0])
            print("✅ Skincare 탭 클릭 성공 (대체 방법)")
        else:
            raise Exception("Skincare 탭을 찾을 수 없습니다")
    
    time.sleep(5)

def collect_product_links(driver, wait):
    """제품 링크 수집 - 100개까지 로드 (순서 유지)"""
    print("📍 제품 링크 수집 중...")
    
    product_links = []  # set 대신 list 사용
    seen_links = set()  # 중복 체크용
    previous_count = 0
    no_change_count = 0
    scroll_attempt = 0
    max_scroll_attempts = 30  # 최대 스크롤 시도 횟수 증가
    
    while len(product_links) < MAX_PRODUCTS and scroll_attempt < max_scroll_attempts:
        scroll_attempt += 1
        
        # 현재 로드된 제품 수집 (순서 유지)
        try:
            products = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/product/detail"]')
            for p in products:
                href = p.get_attribute("href")
                if href and href not in seen_links:
                    product_links.append(href)
                    seen_links.add(href)
            
            current_count = len(product_links)
            print(f"  🔄 스크롤 {scroll_attempt}회: {current_count}개 제품 발견")
            
            # 목표 달성 시 종료
            if current_count >= MAX_PRODUCTS:
                print(f"  ✅ 목표 {MAX_PRODUCTS}개 달성!")
                break
            
            # 제품 수가 변하지 않는 경우 카운트
            if current_count == previous_count:
                no_change_count += 1
                if no_change_count >= 5:
                    print(f"  ⚠ 더 이상 새로운 제품이 로드되지 않음 (현재 {current_count}개)")
                    break
            else:
                no_change_count = 0
                previous_count = current_count
            
            # "More" 버튼 찾기 및 클릭 시도
            try:
                more_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.more-btn, button[class*="more"], button[class*="More"]')
                for btn in more_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", btn)
                            print(f"    ✓ More 버튼 클릭 성공")
                            time.sleep(3)
                            break
                        except:
                            pass
            except:
                pass
            
            # 페이지 끝까지 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 중간 지점으로도 스크롤 (lazy loading 대응)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ⚠ 스크롤 중 오류: {e}")
            time.sleep(2)
    
    # 최대 개수만큼 자르기
    product_links = product_links[:MAX_PRODUCTS]
    
    print(f"\n✅ 최종 {len(product_links)}개 제품 링크 수집 완료")
    print(f"📋 수집 순서: 베스트셀러 페이지 표시 순서대로")
    return product_links

def get_product_name(driver, wait):
    """제품명 추출"""
    try:
        return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'dt[data-testid="product-name"]'))).text.strip()
    except TimeoutException:
        try:
            return driver.find_element(By.CSS_SELECTOR, 'h1, .product-name, .prd-name').text.strip()
        except:
            return "Unknown Product"

def get_product_category(driver):
    """제품 카테고리 추출"""
    try:
        cat_links = driver.find_elements(By.CSS_SELECTOR, "ul.loc_wrap a")
        for link in cat_links:
            href = link.get_attribute("href")
            if href:
                for ctgr_no, name in CATEGORY_MAP.items():
                    if f"ctgrNo={ctgr_no}" in href:
                        return name
        
        if cat_links:
            return cat_links[-1].text.strip()
    except:
        pass
    return "Unknown"

def click_review_tab(driver):
    """리뷰 탭 클릭"""
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(2)
    
    review_tab = None
    try:
        review_tab = driver.find_element(By.CSS_SELECTOR, 'a[href*="#review"]')
    except:
        try:
            review_tab = driver.find_element(By.XPATH, '//a[contains(text(), "Review") or contains(text(), "review") or contains(text(), "리뷰")]')
        except:
            try:
                review_tab = driver.find_element(By.CSS_SELECTOR, '.tab-review, [data-tab="review"]')
            except:
                pass
    
    if review_tab:
        driver.execute_script("arguments[0].scrollIntoView(true);", review_tab)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", review_tab)
        return True
    return False

def load_more_reviews(driver):
    """More 버튼 클릭하여 리뷰 로드"""
    click_count = 0
    for _ in range(MAX_MORE_CLICKS):
        try:
            more_button = driver.find_element(By.CSS_SELECTOR, 'button.review-list-more-btn')
            if more_button.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", more_button)
                click_count += 1
                time.sleep(2)
            else:
                break
        except NoSuchElementException:
            break
        except:
            break
    
    return click_count

def extract_reviews(driver, product_name, product_category):
    """리뷰 데이터 추출"""
    time.sleep(2)
    review_cards = driver.find_elements(By.CSS_SELECTOR, 'div.product-review-unit')
    
    if not review_cards:
        review_cards = driver.find_elements(By.XPATH, '//div[contains(@class,"review-unit") and contains(@id, "list-review")]')
    
    if not review_cards:
        return []
    
    print(f"  📝 총 {len(review_cards)}개 리뷰 발견")
    
    results = []
    for review_idx, review_card in enumerate(review_cards, 1):
        try:
            if review_idx % 10 == 0:
                print(f"    📍 진행중: {review_idx}/{len(review_cards)} 리뷰 처리 완료")
            
            # 날짜 및 피부 정보 추출
            review_date_info = extract_review_date(review_card)
            skin_info = parse_skin_info(review_card)
            
            # 리뷰 텍스트 추출
            review_text = ""
            try:
                review_text = review_card.find_element(By.CSS_SELECTOR, 'div.review-unit-cont-comment').text.strip()
            except:
                try:
                    review_text = review_card.find_element(By.CSS_SELECTOR, '.review-unit-cont .review-unit-cont-comment').text.strip()
                except:
                    continue
            
            if not review_text:
                continue
            
            # 평가 항목 추출
            try:
                eval_list = review_card.find_element(By.CSS_SELECTOR, 'ul.list-review-evlt')
                eval_items = eval_list.find_elements(By.TAG_NAME, 'li')
            except NoSuchElementException:
                # 평가 항목이 없는 경우
                results.append({
                    "product_name": product_name,
                    "product_category": product_category,
                    "evaluation_keyword": "General Review",
                    "star_score": 0,
                    "review_text": review_text,
                    "review_date": review_date_info["review_date"],
                    "review_month": review_date_info["review_month"],
                    "skin_type": skin_info["skin_type"],
                    "skin_concerns": skin_info["skin_concerns"],
                    "collection_timestamp": COLLECTION_TIMESTAMP,
                    "collection_batch": COLLECTION_BATCH
                })
                continue
            
            # 평가 항목별 데이터 저장
            for item in eval_items:
                try:
                    keyword = item.find_element(By.TAG_NAME, 'span').text.strip()
                    star_rating_div = item.find_element(By.CSS_SELECTOR, 'div.review-star-rating')
                    score = get_star_score(star_rating_div)
                    
                    results.append({
                        "product_name": product_name,
                        "product_category": product_category,
                        "evaluation_keyword": keyword,
                        "star_score": score,
                        "review_text": review_text,
                        "review_date": review_date_info["review_date"],
                        "review_month": review_date_info["review_month"],
                        "skin_type": skin_info["skin_type"],
                        "skin_concerns": skin_info["skin_concerns"],
                        "collection_timestamp": COLLECTION_TIMESTAMP,
                        "collection_batch": COLLECTION_BATCH
                    })
                except:
                    continue
        
        except Exception as e:
            continue
    
    return results

def crawl_product(driver, wait, url, idx, total):
    """단일 제품 크롤링"""
    print(f"\n▶ [{idx}/{total}] 제품 처리 중: {url}")
    
    try:
        driver.get(url)
        time.sleep(4)
        
        # 제품 정보 수집
        product_name = get_product_name(driver, wait)
        product_category = get_product_category(driver)
        
        print(f"  제품명: {product_name}")
        print(f"  카테고리: {product_category}")
        
        # 리뷰 탭 클릭
        if not click_review_tab(driver):
            print("  ⚠ 리뷰 탭 찾기 실패 - 스킵")
            return []
        
        print("  ✅ 리뷰 탭 클릭")
        time.sleep(5)
        
        # 더 많은 리뷰 로드
        print("  🔄 More 버튼 클릭하여 리뷰 로딩 중...")
        click_count = load_more_reviews(driver)
        print(f"    ✓ More 버튼 {click_count}회 클릭 완료")
        
        # 리뷰 추출
        results = extract_reviews(driver, product_name, product_category)
        print(f"  ✅ 제품 [{idx}] 완료 - {len(results)}개 데이터 수집")
        
        return results
    
    except Exception as e:
        print(f"  ❌ 제품 [{idx}] 처리 실패: {e}")
        return []

def save_results(results):
    """결과 저장 및 통계 출력"""
    if not results:
        print("\n⚠ 수집된 데이터가 없습니다")
        return
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    df = pd.DataFrame(results)
    output_file = f"{OUTPUT_DIR}/skincare_reviews_complete.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    
    print(f"\n🎉 크롤링 완료!")
    print(f"📊 총 {len(results)}개 데이터 수집")
    print(f"💾 저장 위치: {output_file}")
    
    # 통계 출력
    print("\n📋 수집된 데이터 샘플:")
    print(df.head(10))
    
    print("\n📈 제품별 수집 통계:")
    print(df.groupby('product_name').size())
    
    print("\n📅 월별 리뷰 분포:")
    month_dist = df['review_month'].value_counts().sort_index()
    print(month_dist)
    
    print("\n👤 피부 타입별 분포:")
    print(df['skin_type'].value_counts())
    
    print("\n🔍 피부 고민별 빈도 (Top 10):")
    all_concerns = []
    for concerns in df['skin_concerns'].dropna():
        all_concerns.extend([c.strip() for c in concerns.split(',')])
    if all_concerns:
        concern_counts = pd.Series(all_concerns).value_counts().head(10)
        print(concern_counts)
    
    print(f"\n🕐 수집 시간: {COLLECTION_TIMESTAMP}")
    print(f"📦 수집 배치: {COLLECTION_BATCH}")

# ========================================
# 메인 실행
# ========================================
def main():
    driver, wait = setup_driver()
    
    try:
        # 1. Skincare 카테고리로 이동
        navigate_to_skincare(driver, wait)
        
        # 2. 제품 링크 수집
        product_links = collect_product_links(driver, wait)
        
        # 3. 각 제품 크롤링
        all_results = []
        for idx, url in enumerate(product_links, 1):
            results = crawl_product(driver, wait, url, idx, len(product_links))
            all_results.extend(results)
        
        # 4. 결과 저장
        save_results(all_results)
    
    except Exception as e:
        print(f"\n❌ 전체 프로세스 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print("\n✅ 브라우저 종료")

if __name__ == "__main__":
    main()