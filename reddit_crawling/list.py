import os
import re
import pandas as pd

TOP_CSV = os.path.join("data", "top_products.csv")


STAR_CHARS = r"\*\u2605\u2606"  # * ★ ☆

def clean_product_name(name: str) -> str:
    if not isinstance(name, str):
        return ""

    s = name.strip()

    # 1) 맨 앞에 붙는 "★2025 Awards★" / "*2025 Awards*" 같은 뱃지 제거
    #    예: "★2025 Awards★Anua ...." -> "Anua ...."
    s = re.sub(rf"^\s*[{STAR_CHARS}]+\s*\d{{4}}\s*Awards\s*[{STAR_CHARS}]+\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(rf"^\s*\d{{4}}\s*Awards\s*[{STAR_CHARS}]+\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(rf"^\s*[{STAR_CHARS}]+\s*\d{{4}}\s*Awards\s*", "", s, flags=re.IGNORECASE)

    # 2) 괄호(...) / （...） 안 내용 제거 (여러 번 반복되는 것도 전부 제거)
    #    예: "~~ ( +Refill 30ml+... )" 제거
    s = re.sub(r"\s*\([^)]*\)", "", s)
    s = re.sub(r"\s*（[^）]*）", "", s)  # 전각 괄호

    # (선택) 대괄호[...] 같은 것도 있으면 같이 제거하고 싶을 때
    s = re.sub(r"\s*\[[^\]]*\]", "", s)

    # 3) 공백 정리
    s = re.sub(r"\s+", " ", s).strip()

    # 4) 너무 짧아져버리면 원본 일부라도 남기기(안전장치)
    return s if len(s) >= 3 else name.strip()


def get_reddit_keywords(clean=True):
    df = pd.read_csv(TOP_CSV)

    # 원본 제품명 리스트
    names = (
        df["product_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    if clean:
        cleaned = [clean_product_name(x) for x in names]
        # 순서 유지하면서 중복 제거
        seen = set()
        keywords = []
        for x in cleaned:
            if x and x not in seen:
                keywords.append(x)
                seen.add(x)
        return keywords

    # clean=False면 원본 그대로
    return list(dict.fromkeys([x for x in names if x]))


if __name__ == "__main__":
    reddit_keywords = get_reddit_keywords(clean=True)
    print(len(reddit_keywords))
    print(reddit_keywords[:10])

    # (선택) 정리된 키워드도 파일로 저장해두기
    os.makedirs("data", exist_ok=True)
    pd.DataFrame({"keyword": reddit_keywords}).to_csv("data/reddit_keywords.csv", index=False, encoding="utf-8-sig")
    print("saved -> data/reddit_keywords.csv")
