# main.py
import os
import test
import list as list_module
import redit
from excel_export import reddit_csv_to_excel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

TOP_CSV = os.path.join(DATA_DIR, "top_products.csv")
REDDIT_CSV = os.path.join(DATA_DIR, "reddit_top_relevant_month.csv")
REDDIT_XLSX = os.path.join(DATA_DIR, "reddit_top_relevant_month.xlsx")

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("\n[1/4] 올리브영 Top100 수집 (test.py)")
    test.main()  # data/top_products.csv 생성

    if not os.path.exists(TOP_CSV):
        raise FileNotFoundError(f"Top100 파일 없음: {TOP_CSV}")

    print("\n[2/4] 키워드 정제 (list.py)")
    keywords = list_module.get_reddit_keywords(clean=True)

    print(f"✅ 키워드 {len(keywords)}개")

    print("\n[3/4] 레딧 크롤링 (redit.py)")
    out_csv = redit.main(keywords=keywords)  # data/reddit_top_relevant_month.csv 생성
    if not out_csv:
        out_csv = REDDIT_CSV

    if not os.path.exists(out_csv):
        raise FileNotFoundError(f"Reddit CSV 파일 없음: {out_csv}")

    print("\n[4/4] 엑셀 변환 (excel_export.py)")
    xlsx = reddit_csv_to_excel(out_csv, REDDIT_XLSX)
    print(f"✅ 완료: {xlsx}")

if __name__ == "__main__":
    main()
