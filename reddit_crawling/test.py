from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time
import os
from datetime import datetime

# ===== 기존 설정 그대로 =====
BASE_URL = "https://global.oliveyoung.com/display/page/best-seller?target=pillsTab1Nav1"
MAX_PRODUCTS = 100
OUTPUT_DIR = "data"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # test.py가 있는 폴더
OUTPUT_DIR = os.path.join(BASE_DIR, "data")             # 절대경로 data 폴더
TOP_PRODUCTS_CSV = os.path.join(OUTPUT_DIR, "top_products.csv")  # ✅ import용 변수


COLLECTION_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
COLLECTION_BATCH = f"{datetime.now().year}Q{(datetime.now().month - 1) // 3 + 1}"

# ===== 기존 함수들 그대로(필요한 것만) =====
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)
    return driver, WebDriverWait(driver, 20)

def navigate_to_skincare(driver, wait):
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
    print("📍 제품 링크 수집 중...")

    product_links = []
    seen_links = set()
    previous_count = 0
    no_change_count = 0
    scroll_attempt = 0
    max_scroll_attempts = 30

    while len(product_links) < MAX_PRODUCTS and scroll_attempt < max_scroll_attempts:
        scroll_attempt += 1

        products = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/product/detail"]')
        for p in products:
            href = p.get_attribute("href")
            if href and href not in seen_links:
                product_links.append(href)
                seen_links.add(href)

        current_count = len(product_links)
        print(f"  🔄 스크롤 {scroll_attempt}회: {current_count}개 제품 발견")

        if current_count >= MAX_PRODUCTS:
            print(f"  ✅ 목표 {MAX_PRODUCTS}개 달성!")
            break

        if current_count == previous_count:
            no_change_count += 1
            if no_change_count >= 5:
                print(f"  ⚠ 더 이상 새로운 제품이 로드되지 않음 (현재 {current_count}개)")
                break
        else:
            no_change_count = 0
            previous_count = current_count

        # More 버튼(있으면) 클릭 시도
        try:
            more_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.more-btn, button[class*="more"], button[class*="More"]')
            for btn in more_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", btn)
                        print("    ✓ More 버튼 클릭 성공")
                        time.sleep(3)
                        break
                    except:
                        pass
        except:
            pass

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
        time.sleep(1)

    product_links = product_links[:MAX_PRODUCTS]
    print(f"\n✅ 최종 {len(product_links)}개 제품 링크 수집 완료")
    return product_links

def get_product_name(driver, wait):
    try:
        return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'dt[data-testid="product-name"]'))).text.strip()
    except TimeoutException:
        try:
            return driver.find_element(By.CSS_SELECTOR, 'h1, .product-name, .prd-name').text.strip()
        except:
            return "Unknown Product"

# ===== Top100 이름만 뽑는 main =====
def main():
    driver, wait = setup_driver()

    try:
        navigate_to_skincare(driver, wait)
        product_links = collect_product_links(driver, wait)

        top_rows = []
        for rank, url in enumerate(product_links, 1):
            try:
                driver.get(url)
                time.sleep(3)
                name = get_product_name(driver, wait)

                top_rows.append({
                    "rank": rank,
                    "product_name": name,
                    "product_url": url,
                    "collection_timestamp": COLLECTION_TIMESTAMP,
                    "collection_batch": COLLECTION_BATCH
                })

                print(f"  [TOP] {rank:03d} | {name}")

            except Exception as e:
                print(f"  ⚠ {rank}번 제품 처리 실패: {e}")
                continue

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        pd.DataFrame(top_rows).to_csv(TOP_PRODUCTS_CSV, index=False, encoding="utf-8-sig")


        print(f"\n🎉 Top 제품명 저장 완료: {TOP_PRODUCTS_CSV}")
        print(f"📊 rows={len(top_rows)}")

    finally:
        driver.quit()
        print("\n✅ 브라우저 종료")

if __name__ == "__main__":
    main()
