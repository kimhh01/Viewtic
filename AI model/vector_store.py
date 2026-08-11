from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List, Dict, Any
import os
import logging
from api_config import settings

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """벡터 스토어 관리 클래스"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.vector_store: FAISS = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
    
    def create_vector_store(self, documents: List[Dict[str, Any]]) -> None:
        """문서들로부터 벡터 스토어 생성"""
        try:
            logger.info("벡터 스토어 생성 시작...")
            
            # Dictionary를 Document 객체로 변환
            langchain_docs = []
            for doc in documents:
                langchain_docs.append(
                    Document(
                        page_content=doc["text"],
                        metadata=doc["metadata"]
                    )
                )
            
            # 문서 분할
            logger.info("문서 분할 중...")
            split_docs = self.text_splitter.split_documents(langchain_docs)
            logger.info(f"{len(split_docs)}개의 청크로 분할 완료")
            
            # FAISS 벡터 스토어 생성
            logger.info("임베딩 생성 및 벡터 스토어 구축 중...")
            self.vector_store = FAISS.from_documents(
                documents=split_docs,
                embedding=self.embeddings
            )
            
            logger.info("벡터 스토어 생성 완료")
            
        except Exception as e:
            logger.error(f"벡터 스토어 생성 중 오류: {str(e)}")
            raise
    
    def save_vector_store(self, path: str = None) -> None:
        """벡터 스토어를 디스크에 저장"""
        if self.vector_store is None:
            raise ValueError("저장할 벡터 스토어가 없습니다.")
        
        save_path = path or settings.VECTOR_STORE_PATH
        
        try:
            os.makedirs(save_path, exist_ok=True)
            self.vector_store.save_local(save_path)
            logger.info(f"벡터 스토어 저장 완료: {save_path}")
        except Exception as e:
            logger.error(f"벡터 스토어 저장 중 오류: {str(e)}")
            raise
    
    def load_vector_store(self, path: str = None) -> None:
        """디스크에서 벡터 스토어 로드"""
        load_path = path or settings.VECTOR_STORE_PATH
        
        try:
            if not os.path.exists(load_path):
                raise FileNotFoundError(f"벡터 스토어를 찾을 수 없습니다: {load_path}")
            
            self.vector_store = FAISS.load_local(
                load_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"벡터 스토어 로드 완료: {load_path}")
        except Exception as e:
            logger.error(f"벡터 스토어 로드 중 오류: {str(e)}")
            raise
    
    def similarity_search(
        self,
        query: str,
        k: int = None
    ) -> List[Document]:
        """유사도 검색 수행"""
        if self.vector_store is None:
            raise ValueError("벡터 스토어가 초기화되지 않았습니다.")
        
        k = k or settings.TOP_K_RESULTS
        
        try:
            results = self.vector_store.similarity_search(query, k=k)
            logger.info(f"검색 완료: {len(results)}개 결과 반환")
            return results
        except Exception as e:
            logger.error(f"검색 중 오류: {str(e)}")
            raise
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = None
    ) -> List[tuple]:
        """유사도 점수와 함께 검색 수행"""
        if self.vector_store is None:
            raise ValueError("벡터 스토어가 초기화되지 않았습니다.")
        
        k = k or settings.TOP_K_RESULTS
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            logger.info(f"검색 완료: {len(results)}개 결과 반환 (점수 포함)")
            return results
        except Exception as e:
            logger.error(f"검색 중 오류: {str(e)}")
            raise