import os
from typing import Dict, List
from openai import OpenAI
from rag_system import load_existing_vector_store, VectorStore
from dotenv import load_dotenv


# =========================
# 설정
# =========================
load_dotenv()  # .env 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# LLM 분석 시스템
# =========================
class SkincareAnalyzer:
    """GPT-4를 사용한 스킨케어 인사이트 분석 시스템"""
    
    def __init__(self, vector_store: VectorStore, model: str = "gpt-4-turbo-preview"):
        """
        Args:
            vector_store: RAG 벡터 스토어
            model: 사용할 OpenAI 모델 (gpt-4, gpt-4-turbo-preview 등)
        """
        self.vector_store = vector_store
        self.model = model
        self.conversation_history = []
        
        print(f"✅ SkincareAnalyzer 초기화 완료 (모델: {model})")
    
    def analyze(self, 
                question: str, 
                n_results: int = 5, 
                filter_metadata: Dict = None,
                temperature: float = 0.7,
                use_history: bool = False) -> Dict:
        """
        질문에 대한 분석 수행
        
        Args:
            question: 분석 질문
            n_results: 검색할 문맥 개수
            filter_metadata: 메타데이터 필터 (예: {"product_name": "Product A"})
            temperature: GPT-4 생성 온도 (0.0~2.0)
            use_history: 대화 히스토리 사용 여부
            
        Returns:
            분석 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"🔍 분석 질문: {question}")
        print(f"{'='*60}")
        
        # 1. RAG로 관련 문맥 검색
        print("\n📚 관련 데이터 검색 중...")
        search_results = self.vector_store.search(
            query=question,
            n_results=n_results,
            filter_metadata=filter_metadata
        )
        
        print(f"✅ {len(search_results)}개 관련 청크 발견")
        self._print_search_summary(search_results)
        
        # 2. 문맥 구성
        context = self._build_context(search_results)
        
        # 3. GPT-4로 분석 생성
        print("\n🤖 GPT-4 분석 생성 중...")
        response = self._generate_analysis(
            question=question,
            context=context,
            temperature=temperature,
            use_history=use_history
        )
        
        # 4. 대화 히스토리 업데이트
        if use_history:
            self.conversation_history.append({
                "role": "user",
                "content": question
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
        
        result = {
            'question': question,
            'answer': response,
            'sources': [r['metadata'] for r in search_results],
            'context_used': len(search_results),
            'model': self.model
        }
        
        print(f"\n✅ 분석 완료!")
        return result
    
    def _build_context(self, search_results: List[Dict]) -> str:
        """검색 결과를 문맥 텍스트로 구성"""
        context_parts = []
        
        for i, result in enumerate(search_results, 1):
            context_parts.append(
                f"=== Context {i} ===\n"
                f"Type: {result['metadata']['type']}\n"
                f"Source: {result['metadata'].get('product_name', 'Market-wide data')}\n"
                f"\n{result['content']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _generate_analysis(self, 
                          question: str, 
                          context: str, 
                          temperature: float,
                          use_history: bool) -> str:
        """GPT-4로 분석 생성"""
        
        # 시스템 프롬프트
        system_prompt = """You are an expert skincare product analyst with deep knowledge of cosmetic chemistry, consumer behavior, and market trends.

Your role is to analyze customer review data to provide actionable insights for product development, marketing, and strategy teams.

When analyzing data, you should:

1. **Be Data-Driven**: Always cite specific numbers, percentages, and trends from the provided data
2. **Identify Root Causes**: Go beyond surface-level observations to uncover why patterns exist
3. **Provide Actionable Recommendations**: Give concrete, implementable suggestions
4. **Consider Context**: 
   - Compare temporal trends (quarters)
   - Segment by skin types when relevant
   - Identify product-specific vs market-wide patterns
5. **Highlight Opportunities and Risks**: Balance optimism with caution
6. **Use Clear Structure**: Organize your analysis with clear sections

Response Format:
- Start with a brief executive summary (2-3 sentences)
- Use clear section headers
- Include specific data points and numbers
- End with prioritized action items

Tone: Professional, insightful, and actionable"""

        # 사용자 메시지 구성
        user_message = f"""Based on the following customer review data, please provide a comprehensive analysis:

QUESTION:
{question}

AVAILABLE DATA:
{context}

Please analyze this data thoroughly and provide actionable insights."""

        # 메시지 구성
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 히스토리 포함 (필요시)
        if use_history and self.conversation_history:
            messages.extend(self.conversation_history[-6:])  # 최근 3턴만 포함
        
        messages.append({"role": "user", "content": user_message})
        
        # GPT-4 API 호출
        try:
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = f"GPT-4 API 호출 오류: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def _print_search_summary(self, results: List[Dict]):
        """검색 결과 요약 출력"""
        print("\n검색된 데이터 소스:")
        for i, result in enumerate(results, 1):
            meta = result['metadata']
            print(f"  {i}. [{meta['type']}] ", end="")
            
            if 'product_name' in meta:
                print(f"{meta['product_name']}", end="")
            if 'quarter' in meta:
                print(f" ({meta['quarter']})", end="")
            if 'skin_type' in meta:
                print(f" - {meta['skin_type']}", end="")
            
            print(f" (similarity: {1-result['distance']:.2%})")
    
    def clear_history(self):
        """대화 히스토리 초기화"""
        self.conversation_history = []
        print("🗑️  대화 히스토리가 초기화되었습니다.")
    
    def export_analysis(self, result: Dict, output_path: str):
        """분석 결과를 파일로 저장"""
        import json
        from datetime import datetime
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'question': result['question'],
            'answer': result['answer'],
            'model': result['model'],
            'sources_count': result['context_used'],
            'sources': result['sources']
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 분석 결과 저장: {output_path}")

# =========================
# 편의 함수들
# =========================
def quick_analyze(question: str, 
                 vector_store: VectorStore = None,
                 model: str = "gpt-4-turbo-preview",
                 n_results: int = 5) -> str:
    """빠른 1회성 분석 (히스토리 없음)"""
    
    if vector_store is None:
        vector_store = load_existing_vector_store()
        if vector_store is None:
            return "벡터 스토어를 로드할 수 없습니다."
    
    analyzer = SkincareAnalyzer(vector_store, model=model)
    result = analyzer.analyze(question, n_results=n_results)
    
    return result['answer']

def batch_analyze(questions: List[str],
                 vector_store: VectorStore = None,
                 model: str = "gpt-4-turbo-preview",
                 output_dir: str = "analysis_results") -> List[Dict]:
    """여러 질문을 배치로 분석"""
    
    if vector_store is None:
        vector_store = load_existing_vector_store()
        if vector_store is None:
            print("❌ 벡터 스토어를 로드할 수 없습니다.")
            return []
    
    analyzer = SkincareAnalyzer(vector_store, model=model)
    results = []
    
    os.makedirs(output_dir, exist_ok=True)
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"📊 배치 분석 진행 중: {i}/{len(questions)}")
        print(f"{'='*60}")
        
        result = analyzer.analyze(question)
        results.append(result)
        
        # 각 결과를 파일로 저장
        output_path = os.path.join(output_dir, f"analysis_{i}.json")
        analyzer.export_analysis(result, output_path)
    
    print(f"\n✅ 배치 분석 완료! 총 {len(results)}개 분석 수행")
    return results

# =========================
# 메인 실행 (예시)
# =========================
if __name__ == "__main__":
    # API 키 확인
    if not OPENAI_API_KEY:
        print("❌ 환경변수에 OpenAI API 키를 설정해주세요:")
        print("   export OPENAI_API_KEY='your-key'")
        exit()
    
    print("="*60)
    print("🚀 스킨케어 LLM 분석 시스템 시작")
    print("="*60)
    
    # 1. 벡터 스토어 로드
    vector_store = load_existing_vector_store()
    
    if vector_store is None:
        print("\n❌ 먼저 rag_system.py를 실행하여 벡터 DB를 구축해주세요!")
        exit()
    
    # 2. Analyzer 초기화
    analyzer = SkincareAnalyzer(
        vector_store=vector_store,
        model="gpt-4-turbo-preview"  # 또는 "gpt-4", "gpt-4-1106-preview" 등
    )
    
    # 3. 샘플 질문들
    sample_questions = [
        "Which products have the highest complaints about stickiness? Is this trend increasing over time?",
        "What are the main differences in complaints between oily skin and dry skin users?",
        "Which product shows the most improvement in customer satisfaction over recent quarters?",
        "What are the emerging concerns in the latest quarter across all products?",
        "Which aspects should we prioritize for product improvement based on negative signals?"
    ]
    
    # 4. 첫 번째 질문 분석 (예시)
    result = analyzer.analyze(
        question=sample_questions[0],
        n_results=5,
        temperature=0.7
    )
    
    # 5. 결과 출력
    print(f"\n{'='*60}")
    print("📝 분석 결과")
    print(f"{'='*60}")
    print(f"\n{result['answer']}")
    
    # 6. 결과 저장
    analyzer.export_analysis(result, "sample_analysis.json")
    
    print(f"\n{'='*60}")
    print("✅ 분석 완료!")
    print(f"{'='*60}")
    
    print("\n💡 사용 방법:")
    print("  - analyzer.analyze('your question')으로 새로운 분석")
    print("  - quick_analyze('your question')으로 빠른 1회 분석")
    print("  - batch_analyze([q1, q2, ...])으로 배치 분석")