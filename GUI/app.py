import streamlit as st
import requests
import json
from datetime import datetime
from typing import List, Dict

# 페이지 설정
st.set_page_config(
    page_title="스킨케어 AI 어시스턴트",
    page_icon="💆‍♀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API 엔드포인트
API_BASE_URL = "http://localhost:8000/api/v1"

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF6B9D;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        animation: fadeIn 0.5s;
        color: #111111;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
    }
    .assistant-message {
        background-color: #F3E5F5;
        border-left: 4px solid #9C27B0;
    }
    .context-box {
        background-color: #FFF9C4;
        padding: 1rem;
        border-radius: 5px;
        border-left: 3px solid #FBC02D;
        margin-top: 1rem;
    }
    .metric-card {
        background-color: #F5F5F5;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'api_status' not in st.session_state:
    st.session_state.api_status = None

def check_api_health():
    """API 서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        return False, None
    except Exception as e:
        return False, str(e)

def send_query(query: str, top_k: int = 5, temperature: float = 0.7):
    """단일 질의 전송"""
    try:
        payload = {
            "query": query,
            "top_k": top_k,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        response = requests.post(
            f"{API_BASE_URL}/query",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"오류: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"요청 실패: {str(e)}"

def send_chat(messages: List[Dict], temperature: float = 0.7):
    """대화형 메시지 전송"""
    try:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"오류: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"요청 실패: {str(e)}"

def search_context(query: str, top_k: int = 3):
    """컨텍스트 검색"""
    try:
        payload = {
            "query": query,
            "top_k": top_k
        }
        
        response = requests.post(
            f"{API_BASE_URL}/search",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"오류: {response.status_code}"
    except Exception as e:
        return False, f"요청 실패: {str(e)}"

# 메인 헤더
st.markdown('<div class="main-header">💆‍♀️ 스킨케어 AI 어시스턴트</div>', unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    
    # API 상태 체크
    st.subheader("🔌 서버 상태")
    if st.button("상태 확인", use_container_width=True):
        is_healthy, status_data = check_api_health()
        st.session_state.api_status = is_healthy
        
        if is_healthy:
            st.success("✅ 서버 연결됨")
            if status_data:
                st.json(status_data)
        else:
            st.error("❌ 서버 연결 실패")
            st.info("백엔드 서버를 시작해주세요:\n```bash\ncd AI_model\npython main.py\n```")
    
    st.divider()
    
    # 모드 선택
    st.subheader("💬 대화 모드")
    conversation_mode = st.radio(
        "모드 선택",
        ["단일 질문", "연속 대화"],
        help="단일 질문: 매번 새로운 질문\n연속 대화: 이전 대화 기억"
    )
    
    st.divider()
    
    # 고급 설정
    st.subheader("🎛️ 고급 설정")
    
    top_k = st.slider(
        "검색 문서 수",
        min_value=1,
        max_value=10,
        value=5,
        help="검색할 관련 문서의 개수"
    )
    
    temperature = st.slider(
        "창의성 (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="높을수록 더 창의적인 답변"
    )
    
    show_context = st.checkbox(
        "참조 문서 표시",
        value=True,
        help="AI가 참고한 문서 정보 표시"
    )
    
    st.divider()
    
    # 대화 기록 관리
    if st.button("🗑️ 대화 기록 지우기", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# 메인 컨텐츠 영역
tab1, tab2 = st.tabs(["💬 채팅", "🔍 문서 검색"])

with tab1:
    # 채팅 인터페이스
    st.subheader("질문하기")
    
    # 대화 기록 표시
    chat_container = st.container()
    
    with chat_container:
        for i, chat in enumerate(st.session_state.chat_history):
            if chat['role'] == 'user':
                st.markdown(
                    f'<div class="chat-message user-message">👤 <strong>나:</strong><br>{chat["content"]}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="chat-message assistant-message">🤖 <strong>AI:</strong><br>{chat["content"]}</div>',
                    unsafe_allow_html=True
                )
                
                # 컨텍스트 정보 표시
                if show_context and 'context' in chat:
                    with st.expander(f"📚 참조 문서 ({len(chat['context'])}개)"):
                        for idx, ctx in enumerate(chat['context'], 1):
                            st.markdown(f"**[문서 {idx}]** (유사도: {ctx['similarity_score']:.4f})")
                            st.text(ctx['content'][:200] + "...")
                            st.caption(f"출처: {ctx['metadata']['source']}")
                            st.divider()
                
                # 토큰 사용량 표시
                if 'tokens_used' in chat:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("입력 토큰", chat['tokens_used'].get('prompt', 0))
                    with col2:
                        st.metric("출력 토큰", chat['tokens_used'].get('completion', 0))
                    with col3:
                        st.metric("총 토큰", chat['tokens_used'].get('total', 0))
    
    # 입력 영역
    st.divider()
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "질문을 입력하세요",
            placeholder="예: 건성 피부에 좋은 제품을 추천해주세요",
            label_visibility="collapsed"
        )
    
    with col2:
        send_button = st.button("전송 📤", use_container_width=True)
    
    # 예시 질문 버튼
    st.caption("💡 예시 질문:")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("건성 피부 제품 추천", use_container_width=True):
            user_input = "건성 피부에 좋은 제품을 추천해주세요"
            send_button = True
    
    with col2:
        if st.button("민감성 피부 관리법", use_container_width=True):
            user_input = "민감성 피부 관리 방법을 알려주세요"
            send_button = True
    
    with col3:
        if st.button("여드름 제품 추천", use_container_width=True):
            user_input = "여드름 피부에 좋은 제품은?"
            send_button = True
    
    # 메시지 전송 처리
    if send_button and user_input:
        # 사용자 메시지 추가
        st.session_state.chat_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now()
        })
        
        with st.spinner("AI가 답변을 생성하고 있습니다..."):
            if conversation_mode == "단일 질문":
                # 단일 질의 모드
                success, result = send_query(user_input, top_k, temperature)
            else:
                # 연속 대화 모드
                messages = [
                    {"role": chat['role'], "content": chat['content']}
                    for chat in st.session_state.chat_history
                ]
                success, result = send_chat(messages, temperature)
            
            if success:
                # AI 응답 추가
                assistant_message = {
                    'role': 'assistant',
                    'content': result.get('answer', ''),
                    'context': result.get('context', []),
                    'tokens_used': result.get('tokens_used', {}),
                    'timestamp': datetime.now()
                }
                st.session_state.chat_history.append(assistant_message)
                st.rerun()
            else:
                st.error(f"❌ {result}")

with tab2:
    # 문서 검색 인터페이스
    st.subheader("문서 검색")
    st.caption("AI 응답 없이 관련 문서만 검색합니다")
    
    search_query = st.text_input(
        "검색어를 입력하세요",
        placeholder="예: 수분 크림"
    )
    
    search_top_k = st.slider(
        "검색 결과 수",
        min_value=1,
        max_value=10,
        value=5
    )
    
    if st.button("🔍 검색", use_container_width=True):
        if search_query:
            with st.spinner("검색 중..."):
                success, result = search_context(search_query, search_top_k)
                
                if success:
                    st.success(f"✅ {result['count']}개의 문서를 찾았습니다")
                    
                    for idx, doc in enumerate(result['results'], 1):
                        with st.expander(f"📄 문서 {idx} (유사도: {doc['similarity_score']:.4f})"):
                            st.markdown(f"**출처:** {doc['metadata']['source']}")
                            st.markdown(f"**타입:** {doc['metadata']['type']}")
                            st.divider()
                            st.text(doc['content'])
                else:
                    st.error(f"❌ {result}")
        else:
            st.warning("검색어를 입력해주세요")

# 푸터
st.divider()
st.caption("💡 Powered by GPT-4 & FAISS | 🔒 모든 데이터는 로컬에서 처리됩니다")