from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

# 요청 모델 정의
class QueryRequest(BaseModel):
    query: str = Field(..., description="질문 또는 검색 쿼리", min_length=1)
    top_k: Optional[int] = Field(None, description="검색할 문서 수", ge=1, le=20)
    temperature: Optional[float] = Field(0.7, description="응답 생성 온도", ge=0, le=2)
    max_tokens: Optional[int] = Field(1000, description="최대 토큰 수", ge=100, le=4000)

class ChatMessage(BaseModel):
    role: str = Field(..., description="메시지 역할 (user/assistant/system)")
    content: str = Field(..., description="메시지 내용")

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="대화 메시지 목록")
    temperature: Optional[float] = Field(0.7, description="응답 생성 온도", ge=0, le=2)
    max_tokens: Optional[int] = Field(1000, description="최대 토큰 수", ge=100, le=4000)

class SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리", min_length=1)
    top_k: Optional[int] = Field(5, description="검색할 문서 수", ge=1, le=20)

# 응답 모델 정의
class QueryResponse(BaseModel):
    query: str
    answer: str
    context: List[Dict[str, Any]]
    model: str
    tokens_used: Dict[str, int]

class ChatResponse(BaseModel):
    answer: str
    context: List[Dict[str, Any]]
    tokens_used: Dict[str, int]

class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    count: int

class HealthResponse(BaseModel):
    status: str
    message: str
    initialized: bool

# 전역 RAG 시스템 (main.py에서 주입됨)
rag_system = None

def set_rag_system(rag):
    """RAG 시스템 설정"""
    global rag_system
    rag_system = rag

# 라우트 정의
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "message": "RAG API is running",
        "initialized": rag_system.is_initialized if rag_system else False
    }

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """단일 질문에 대한 RAG 응답 생성"""
    if not rag_system or not rag_system.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG 시스템이 초기화되지 않았습니다."
        )
    
    try:
        logger.info(f"Query 요청: {request.query[:50]}...")
        
        result = rag_system.generate_response(
            query=request.query,
            top_k=request.top_k,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Query 처리 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"응답 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """대화형 인터페이스"""
    if not rag_system or not rag_system.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG 시스템이 초기화되지 않았습니다."
        )
    
    try:
        logger.info(f"Chat 요청: {len(request.messages)}개 메시지")
        
        # Pydantic 모델을 딕셔너리로 변환
        messages = [msg.dict() for msg in request.messages]
        
        result = rag_system.chat(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Chat 처리 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대화 처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    """컨텍스트 검색만 수행 (GPT 응답 없이)"""
    if not rag_system or not rag_system.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG 시스템이 초기화되지 않았습니다."
        )
    
    try:
        logger.info(f"Search 요청: {request.query[:50]}...")
        
        results = rag_system.retrieve_context(
            query=request.query,
            top_k=request.top_k
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Search 처리 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/rebuild")
async def rebuild_vector_store():
    """벡터 스토어 재구축"""
    if not rag_system:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG 시스템이 초기화되지 않았습니다."
        )
    
    try:
        logger.info("벡터 스토어 재구축 시작...")
        rag_system.initialize(force_rebuild=True)
        logger.info("벡터 스토어 재구축 완료")
        
        return {
            "status": "success",
            "message": "벡터 스토어가 성공적으로 재구축되었습니다."
        }
        
    except Exception as e:
        logger.error(f"벡터 스토어 재구축 중 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"벡터 스토어 재구축 중 오류가 발생했습니다: {str(e)}"
        )