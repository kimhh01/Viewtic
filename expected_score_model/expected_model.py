# 단순히 점수 계산 해서 기대 점수를 메기는 코드 

import json
import os
from collections import defaultdict

# =========================
# 1. 파일 경로 설정
# =========================
input_file = "data/skincare_reviews_for_llm_analysis_quarterly.json"
output_file = "data/skincare_category_expectation_trends_quarterly.json"

os.makedirs("data", exist_ok=True)

# =========================
# 2. JSON 로드
# =========================
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# =========================
# 3. 기대점수 계산 함수
# =========================
def calculate_expectation_score(positive, negative, review_count):
    """
    기대점수 정의:
    (positive_count - negative_count) / review_count
    """
    if review_count == 0:
        return 0.0
    return (positive - negative) / review_count


# =========================
# 4. 카테고리별 가중 합 집계
# =========================
"""
구조:
category_trends[category][quarter][aspect] = {
    "weighted_sum": Σ(expectation_score * review_count),
    "review_sum": Σ(review_count),
    "product_count": 제품 수
}
"""
category_trends = defaultdict(
    lambda: defaultdict(
        lambda: defaultdict(
            lambda: {
                "weighted_sum": 0.0,
                "review_sum": 0,
                "product_count": 0
            }
        )
    )
)

for product in data["products"]:
    category = product.get("category", "unknown")

    for quarter, q_data in product.get("quarterly_trends", {}).items():
        review_count = q_data.get("review_count", 0)

        for aspect, signal in q_data.get("signals", {}).items():
            pos = signal.get("positive_count", 0)
            neg = signal.get("negative_count", 0)

            expectation = calculate_expectation_score(pos, neg, review_count)

            category_trends[category][quarter][aspect]["weighted_sum"] += (
                expectation * review_count
            )
            category_trends[category][quarter][aspect]["review_sum"] += review_count
            category_trends[category][quarter][aspect]["product_count"] += 1


# =========================
# 5. 카테고리별 최종 기대점수 계산
# =========================
category_expectation_scores = defaultdict(dict)

for category, quarters in category_trends.items():
    for quarter, aspects in quarters.items():
        category_expectation_scores[category][quarter] = {}

        for aspect, values in aspects.items():
            if values["review_sum"] > 0:
                score = values["weighted_sum"] / values["review_sum"]
            else:
                score = 0.0

            category_expectation_scores[category][quarter][aspect] = {
                "expectation_score": round(score, 4),
                "total_review_count": values["review_sum"],
                "product_count": values["product_count"]
            }


# =========================
# 6. 분기별 기대점수 변화량 계산
# =========================
def calculate_quarterly_delta(category_data):
    """
    분기 간 기대점수 변화량 계산
    """
    sorted_quarters = sorted(category_data.keys())
    delta_result = defaultdict(dict)

    for i in range(1, len(sorted_quarters)):
        prev_q = sorted_quarters[i - 1]
        curr_q = sorted_quarters[i]

        for aspect in category_data[curr_q]:
            if aspect in category_data[prev_q]:
                delta = (
                    category_data[curr_q][aspect]["expectation_score"]
                    - category_data[prev_q][aspect]["expectation_score"]
                )
                delta_result[curr_q][aspect] = round(delta, 4)

    return dict(delta_result)


category_expectation_deltas = {
    category: calculate_quarterly_delta(quarters)
    for category, quarters in category_expectation_scores.items()
}


# =========================
# 7. 최종 결과 JSON 구성
# =========================
final_output = {
    "metadata": {
        "source_file": input_file,
        "analysis_unit": "category",
        "score_definition": "(positive_count - negative_count) / review_count",
        "aggregation_method": "weighted_average_by_review_count"
    },
    "category_expectation_scores": category_expectation_scores,
    "category_expectation_score_deltas": category_expectation_deltas
}

# =========================
# 8. 결과 저장
# =========================
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(final_output, f, ensure_ascii=False, indent=2)

print(f"✅ 카테고리별 기대점수 분석 결과 저장 완료: {output_file}")
