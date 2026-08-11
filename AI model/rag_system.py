from openai import OpenAI
from typing import List, Dict, Any
import logging
from api_config import settings
from vector_store import VectorStoreManager
from data_loader import DataLoader

logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG (Retrieval-Augmented Generation) 시스템"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.vector_store_manager = VectorStoreManager()
        self.data_loader = DataLoader()
        self.is_initialized = False
    
    def initialize(self, force_rebuild: bool = False) -> None:
        """RAG 시스템 초기화"""
        try:
            logger.info("RAG 시스템 초기화 시작...")
            
            # 벡터 스토어가 이미 존재하는지 확인
            import os
            vector_store_exists = os.path.exists(settings.VECTOR_STORE_PATH)
            
            if vector_store_exists and not force_rebuild:
                logger.info("기존 벡터 스토어 로드 중...")
                self.vector_store_manager.load_vector_store()
            else:
                logger.info("새로운 벡터 스토어 생성 중...")
                # 데이터 로드
                documents = self.data_loader.get_all_documents()
                
                # 벡터 스토어 생성
                self.vector_store_manager.create_vector_store(documents)
                
                # 벡터 스토어 저장
                self.vector_store_manager.save_vector_store()
            
            self.is_initialized = True
            logger.info("RAG 시스템 초기화 완료")
            
        except Exception as e:
            logger.error(f"RAG 시스템 초기화 중 오류: {str(e)}")
            raise
    
    def retrieve_context(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """쿼리와 관련된 컨텍스트 검색"""
        if not self.is_initialized:
            raise ValueError("RAG 시스템이 초기화되지 않았습니다.")
        
        top_k = top_k or settings.TOP_K_RESULTS
        
        try:
            # 유사도 검색 (점수 포함)
            results = self.vector_store_manager.similarity_search_with_score(
                query, k=top_k
            )
            
            # 결과 포맷팅
            context_list = []
            for doc, score in results:
                context_list.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": float(score)
                })
            
            return context_list
            
        except Exception as e:
            logger.error(f"컨텍스트 검색 중 오류: {str(e)}")
            raise
    
    def generate_prompt(self, query: str, context_list: List[Dict[str, Any]]) -> str:
        """컨텍스트를 포함한 프롬프트 생성"""
        context_text = "\n\n".join([
            f"[문서 {i+1}] (유사도: {ctx['similarity_score']:.4f})\n{ctx['content']}"
            for i, ctx in enumerate(context_list)
        ])
        
        prompt = f"""다음은 스킨케어 제품 리뷰 및 분석 데이터베이스에서 검색된 관련 정보입니다:

{context_text}

위의 정보를 바탕으로 다음 질문에 답변해주세요:
{query}

답변 시 다음 사항을 고려해주세요:
1. 제공된 데이터를 기반으로 정확하게 답변하세요.
2. 데이터에 없는 내용은 추측하지 마세요.
3. 가능한 한 구체적이고 유용한 정보를 제공하세요.
4. 필요한 경우 데이터의 출처(리뷰/분석)를 명시하세요.
"""
        return prompt
    
    def generate_response(
        self,
        query: str,
        top_k: int = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """RAG를 사용한 응답 생성"""
        if not self.is_initialized:
            raise ValueError("RAG 시스템이 초기화되지 않았습니다.")
        
        try:
            logger.info(f"질문 처리 중: {query[:50]}...")
            
            # 1. 관련 컨텍스트 검색
            context_list = self.retrieve_context(query, top_k)
            logger.info(f"{len(context_list)}개의 관련 문서 검색 완료")
            
            # 2. 프롬프트 생성
            prompt = self.generate_prompt(query, context_list)
            
            # 3. GPT-4로 응답 생성
            logger.info("GPT-4 응답 생성 중...")
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 스킨케어 제품 전문가입니다. 제공된 데이터를 기반으로 정확하고 유용한 정보를 제공합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            
            result = {
                "query": query,
                "answer": answer,
                "context": context_list,
                "model": settings.OPENAI_MODEL,
                "tokens_used": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
            }
            
            logger.info("응답 생성 완료")
            return result
            
        except Exception as e:
            logger.error(f"응답 생성 중 오류: {str(e)}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """대화형 인터페이스 (컨텍스트 검색 포함)"""
        if not self.is_initialized:
            raise ValueError("RAG 시스템이 초기화되지 않았습니다.")
        
        try:
            # 마지막 사용자 메시지에서 컨텍스트 검색
            last_user_message = None
            for msg in reversed(messages):
                if msg["role"] == "user":
                    last_user_message = msg["content"]
                    break
            
            if not last_user_message:
                raise ValueError("사용자 메시지가 없습니다.")
            
            # 관련 컨텍스트 검색
            context_list = self.retrieve_context(last_user_message)
            
            # 시스템 메시지에 컨텍스트 추가
            context_text = "\n\n".join([
                f"[참고 문서 {i+1}]\n{ctx['content']}"
                for i, ctx in enumerate(context_list)
            ])
            
            system_message = {
                "role": "system",
                "content": f"""당신은 스킨케어 제품 전문가입니다. 다음 데이터베이스 정보를 참고하여 답변하세요:

{context_text}"""
            }
            
            # API 호출
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[system_message] + messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "context": context_list,
                "tokens_used": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"대화 처리 중 오류: {str(e)}")
            raise