from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from contextlib import asynccontextmanager

from api_config import settings
from rag_system import RAGSystem
from api_routes import router, set_rag_system


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# RAG 시스템 인스턴스
rag_system = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수"""
    # 시작 시
    global rag_system
    
    try:
        logger.info("=" * 50)
        logger.info("RAG 시스템 초기화 시작")
        logger.info("=" * 50)
        
        # 설정 검증
        settings.validate()
        logger.info("✓ 설정 검증 완료")
        
        # RAG 시스템 초기화
        rag_system = RAGSystem()
        rag_system.initialize()
        
        # API 라우터에 RAG 시스템 주입
        set_rag_system(rag_system)
        
        logger.info("=" * 50)
        logger.info("✓ RAG 시스템 초기화 완료")
        logger.info(f"✓ API 서버 시작: http://{settings.API_HOST}:{settings.API_PORT}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"✗ 초기화 실패: {str(e)}")
        raise
    
    yield
    
    # 종료 시
    logger.info("RAG 시스템 종료 중...")

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Skincare RAG API",
    description="스킨케어 제품 리뷰 및 분석을 위한 RAG 기반 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 예외 처리 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error occurred",
            "error": str(exc)
        }
    )

# 라우터 등록
app.include_router(router, prefix="/api/v1", tags=["RAG"])

# 루트 엔드포인트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Skincare RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

# API 문서 설명
@app.get("/api")
async def api_info():
    """API 정보"""
    return {
        "endpoints": {
            "health": {
                "method": "GET",
                "path": "/api/v1/health",
                "description": "API 상태 확인"
            },
            "query": {
                "method": "POST",
                "path": "/api/v1/query",
                "description": "단일 질문에 대한 RAG 응답 생성"
            },
            "chat": {
                "method": "POST",
                "path": "/api/v1/chat",
                "description": "대화형 인터페이스"
            },
            "search": {
                "method": "POST",
                "path": "/api/v1/search",
                "description": "컨텍스트 검색만 수행"
            },
            "rebuild": {
                "method": "POST",
                "path": "/api/v1/rebuild",
                "description": "벡터 스토어 재구축"
            }
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )