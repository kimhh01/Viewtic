import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from rag_system import load_existing_vector_store
from llm_analyzer import SkincareAnalyzer

app = FastAPI(title="Skincare Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#요청 json 모델
class ChatRequest(BaseModel):
    question: str
    n_results: int = 5
    temperature: float = 0.7
    conversation_history: list = []
    filter_metadata: Optional[Dict[str, Any]] = None
    
#벡터 스토어 로드 및 분석기 초기화
vector_store = load_existing_vector_store()
_analyzer = SkincareAnalyzer(vector_store, model="gpt-4-turbo-preview") if vector_store else None

#헬스체크 엔드포인트
@app.get("/health")
def health():
    return {
        "status": "healthy" if _analyzer else "degraded",
        "vector_store_loaded": _analyzer is not None
    }

#예시 질문 엔드포인트
@app.get("/examples")
def examples():
    return {
        "examples": [
            "끈적임 불만이 가장 많은 제품은?",
            "지성 피부와 건성 피부의 불만 차이는?",
            "최근 분기에 개선된 제품은?",
            "질감 관련 불만이 증가하는 추세인가요?",
            "가장 우선적으로 개선할 부분은?"
        ]
    }


@app.post("/chat")
def chat(req: ChatRequest):

    # 분석기 초기화 실패 시 오류 반환
    if _analyzer is None:
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder({"answer": " analyzer 초기화 실패", "sources": []})
        )

    try:
        result = _analyzer.analyze(
            question=req.question,
            n_results=req.n_results,
            filter_metadata=req.filter_metadata,
            temperature=req.temperature,
            use_history=False
        )
        payload = {"answer": result.get("answer", ""), "sources": result.get("sources", [])}
        return JSONResponse(content=jsonable_encoder(payload))

    except Exception as e:
        # 콘솔에도 찍고
        print(" /chat error:", repr(e))
        print(traceback.format_exc())

        # 클라이언트에도 원인 보내기(디버깅용)
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder({
                "answer": f" 서버 내부 오류: {type(e).__name__}: {e}",
                "sources": []
            })
        )
