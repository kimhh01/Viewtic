import os
from dotenv import load_dotenv
from typing import Optional

# .env 파일 로드
load_dotenv()

class Settings:
    """애플리케이션 설정 클래스"""
    
    # OpenAI API 설정
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # 데이터 파일 경로
    REVIEWS_FILE: str = os.getenv("REVIEWS_FILE", "data/integrated_reviews.csv")
    SKINCARE_FILE: str = os.getenv("SKINCARE_FILE", "data/integrated_skincare_analysis.csv")
    
    # RAG 설정
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))
    
    # API 설정
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Vector Store 경로
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "vector_store")
    
    def validate(self) -> bool:
        """필수 설정 값 검증"""
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다.")
        
        if not os.path.exists(self.REVIEWS_FILE):
            raise FileNotFoundError(f"리뷰 파일을 찾을 수 없습니다: {self.REVIEWS_FILE}")
        
        if not os.path.exists(self.SKINCARE_FILE):
            raise FileNotFoundError(f"스킨케어 분석 파일을 찾을 수 없습니다: {self.SKINCARE_FILE}")
        
        return True

# 전역 설정 객체
settings = Settings()