import json
import pandas as pd
from typing import List, Dict, Any
from api_config import settings
import logging

# =========================
# 로깅 설정
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """데이터 파일 로딩 및 전처리 클래스"""

    def __init__(self):
        self.reviews_df: pd.DataFrame | None = None
        self.skincare_df: pd.DataFrame | None = None

    # =========================
    # 데이터 로딩
    # =========================
    def load_data(self) -> None:
        """
        리뷰 / 스킨케어 데이터 로드
        - CSV / JSON 자동 처리
        - dict, list, str 혼합 구조 모두 대응
        """
        try:
            # ---------- 리뷰 데이터 ----------
            logger.info(f"리뷰 데이터 로딩 중: {settings.REVIEWS_FILE}")

            if settings.REVIEWS_FILE.endswith(".csv"):
                # 탭 구분 TSV 대응
                self.reviews_df = pd.read_csv(
                    settings.REVIEWS_FILE,
                    sep="\t",
                    engine="python",
                    encoding="utf-8"
                )

            elif settings.REVIEWS_FILE.endswith(".json"):
                self.reviews_df = self._load_json_as_dataframe(settings.REVIEWS_FILE)

            else:
                raise ValueError("지원하지 않는 리뷰 파일 형식입니다.")

            logger.info(f"리뷰 데이터 로딩 완료: {len(self.reviews_df)} 행")

            # ---------- 스킨케어 데이터 ----------
            logger.info(f"스킨케어 분석 데이터 로딩 중: {settings.SKINCARE_FILE}")

            if settings.SKINCARE_FILE.endswith(".csv"):
                self.skincare_df = pd.read_csv(
                    settings.SKINCARE_FILE,
                    sep="\t",
                    engine="python",
                    encoding="utf-8"
                )

            elif settings.SKINCARE_FILE.endswith(".json"):
                self.skincare_df = self._load_json_as_dataframe(settings.SKINCARE_FILE)

            else:
                raise ValueError("지원하지 않는 스킨케어 파일 형식입니다.")

            logger.info(f"스킨케어 분석 데이터 로딩 완료: {len(self.skincare_df)} 행")

        except Exception as e:
            logger.error(f"데이터 로딩 중 오류 발생: {str(e)}")
            raise

    # =========================
    # JSON → DataFrame 변환
    # =========================
    def _load_json_as_dataframe(self, file_path: str) -> pd.DataFrame:
        """
        어떤 형태의 JSON이 와도 DataFrame으로 안전하게 변환
        """
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        # dict → list[dict]
        if isinstance(raw_data, dict):
            raw_data = [raw_data]

        processed_rows = []

        for row in raw_data:
            # row가 dict가 아닌 경우 (str, 숫자 등)
            if not isinstance(row, dict):
                processed_rows.append({
                    "raw_text": str(row)
                })
                continue

            new_row = {}
            for key, value in row.items():
                # 내부 dict / list → JSON 문자열로 변환
                if isinstance(value, (dict, list)):
                    new_row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    new_row[key] = value

            processed_rows.append(new_row)

        return pd.DataFrame(processed_rows)

    # =========================
    # 리뷰 전처리
    # =========================
    def preprocess_reviews(self) -> List[Dict[str, Any]]:
        """리뷰 데이터를 RAG 문서 형태로 변환"""
        if self.reviews_df is None:
            raise ValueError("리뷰 데이터가 로드되지 않았습니다.")

        documents = []

        for idx, row in self.reviews_df.iterrows():
            text_parts = []

            for col in self.reviews_df.columns:
                value = row[col]
                if pd.notna(value):
                    text_parts.append(f"{col}: {value}")

            documents.append({
                "text": "\n".join(text_parts),
                "metadata": {
                    "source": "reviews",
                    "index": idx,
                    "type": "review"
                }
            })

        logger.info(f"리뷰 문서 {len(documents)}개 생성 완료")
        return documents

    # =========================
    # 스킨케어 전처리
    # =========================
    def preprocess_skincare(self) -> List[Dict[str, Any]]:
        """스킨케어 분석 데이터를 RAG 문서 형태로 변환"""
        if self.skincare_df is None:
            raise ValueError("스킨케어 데이터가 로드되지 않았습니다.")

        documents = []

        for idx, row in self.skincare_df.iterrows():
            text_parts = []

            for col in self.skincare_df.columns:
                value = row[col]
                if pd.notna(value):
                    text_parts.append(f"{col}: {value}")

            documents.append({
                "text": "\n".join(text_parts),
                "metadata": {
                    "source": "skincare_analysis",
                    "index": idx,
                    "type": "analysis"
                }
            })

        logger.info(f"스킨케어 분석 문서 {len(documents)}개 생성 완료")
        return documents

    # =========================
    # 전체 문서 반환
    # =========================
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """RAG에 사용할 전체 문서 반환"""
        if self.reviews_df is None or self.skincare_df is None:
            self.load_data()

        reviews_docs = self.preprocess_reviews()
        skincare_docs = self.preprocess_skincare()

        all_docs = reviews_docs + skincare_docs
        logger.info(f"총 {len(all_docs)}개 문서 준비 완료")

        return all_docs
