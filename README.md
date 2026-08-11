# 💆‍♀️ 스킨케어 AI 어시스턴트

GPT-4 기반 RAG(Retrieval-Augmented Generation) 시스템을 활용한 스킨케어 제품 추천 및 상담 AI 서비스

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-purple)

## 🌟 주요 기능

- 🤖 **자연어 대화**: 일상적인 대화로 스킨케어 제품 추천 및 상담
- 📚 **RAG 기반**: 실제 리뷰와 분석 데이터를 기반으로 정확한 정보 제공
- 💬 **연속 대화**: 이전 대화 맥락을 기억하는 지능형 대화
- 🔍 **스마트 검색**: FAISS 벡터 검색으로 관련 정보 빠르게 찾기
- 🎨 **직관적 GUI**: Streamlit 기반의 아름다운 웹 인터페이스
- ⚡ **빠른 응답**: 최적화된 벡터 스토어로 빠른 검색

## 🏗️ 시스템 구조

```
┌─────────────────────────────────────────────────────────┐
│                     사용자 (웹 브라우저)                  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              GUI (Streamlit) - Port 8501                │
│  - 채팅 인터페이스                                        │
│  - 문서 검색                                             │
│  - 설정 관리                                             │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/REST API
                        ▼
┌─────────────────────────────────────────────────────────┐
│           백엔드 (FastAPI) - Port 8000                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │            RAG System (rag_system.py)            │  │
│  ├───────────────────────────────────────────────────┤  │
│  │  Vector Store    │  Data Loader  │  GPT-4 API   │  │
│  │   (FAISS)        │  (Pandas)     │  (OpenAI)    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  API Endpoints:                                          │
│  - POST /api/v1/query    (단일 질문)                     │
│  - POST /api/v1/chat     (연속 대화)                     │
│  - POST /api/v1/search   (문서 검색)                     │
│  - GET  /api/v1/health   (상태 확인)                     │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    데이터 소스                           │
│  - integrated_reviews.csv (리뷰 데이터)                  │
│  - integrated_skincare_analysis.csv (분석 데이터)        │
└─────────────────────────────────────────────────────────┘
```

## 📦 설치 방법

### 빠른 시작

1. **저장소 클론 및 이동**
```bash
git clone <repository-url>
cd skincare-rag-project
```

2. **백엔드 설정**
```bash
cd AI_model
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **환경 변수 설정**
```bash
# AI_model/.env 파일 생성
OPENAI_API_KEY=your-api-key-here
```

4. **데이터 파일 배치**
```bash
# AI_model/data/ 폴더에 CSV 파일 복사
cp your-data/integrated_reviews.csv AI_model/data/
cp your-data/integrated_skincare_analysis.csv AI_model/data/
```

5. **실행**
```bash
# 터미널 1: 백엔드
./start_backend.sh  # Windows: start_backend.bat

# 터미널 2: GUI
./start_gui.sh      # Windows: start_gui.bat
```


## 🎯 사용 예시

### 1. 단순 질문

```
사용자: "건성 피부에 좋은 제품을 추천해주세요"

AI: "건성 피부에는 수분 보충이 중요합니다. 데이터를 분석한 결과, 
다음 제품들이 높은 평가를 받았습니다:

1. [제품명] - 히알루론산 함유로 깊은 수분 공급
2. [제품명] - 세라마이드로 피부 장벽 강화
3. [제품명] - 가벼운 텍스처로 흡수가 빠름

각 제품의 주요 성분과 사용자 리뷰를 확인하시겠어요?"
```

### 2. 연속 대화

```
사용자: "지성 피부에 좋은 클렌저 추천해줘"
AI: "지성 피부에는 유분 조절 클렌저가 좋습니다..."

사용자: "그럼 토너는?"
AI: "앞서 추천한 클렌저와 함께 사용하기 좋은 토너로는..."
```

### 3. 문서 검색

```
검색어: "여드름"
→ 여드름 관련 리뷰 5개, 분석 데이터 3개 검색됨
→ 각 문서의 유사도 점수와 내용 미리보기 제공
```

## 🛠️ 기술 스택

### 백엔드 (AI_model/)
- **FastAPI**: REST API 프레임워크
- **LangChain**: RAG 파이프라인 구성
- **FAISS**: 벡터 유사도 검색
- **OpenAI GPT-4**: 자연어 이해 및 생성
- **Pandas**: 데이터 처리
- **Python-dotenv**: 환경 변수 관리

### 프론트엔드 (GUI/)
- **Streamlit**: 웹 인터페이스
- **Requests**: HTTP 클라이언트

## 📊 성능

- **초기 로딩**: 3-5분 (벡터 스토어 생성)
- **이후 시작**: 10-30초
- **검색 속도**: < 1초
- **응답 생성**: 3-10초 (GPT-4 속도에 따름)

## 🔒 보안

- API 키는 `.env` 파일에 안전하게 보관
- 로컬에서만 실행 (외부 노출 없음)
- 데이터는 서버에 저장되지 않음

### 주요 엔드포인트

#### POST /api/v1/query
단일 질문에 대한 답변 생성

```json
{
  "query": "건성 피부에 좋은 제품은?",
  "top_k": 5,
  "temperature": 0.7
}
```

#### POST /api/v1/chat
연속 대화

```json
{
  "messages": [
    {"role": "user", "content": "여드름 제품 추천해줘"},
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "가격대는?"}
  ]
}
```

#### POST /api/v1/search
문서 검색만 (GPT 없이)

```json
{
  "query": "수분 크림",
  "top_k": 3
}
```

## 🎨 커스터마이징

### 모델 변경
`.env` 파일에서:
```env
OPENAI_MODEL=gpt-4-turbo  # 또는 gpt-3.5-turbo
```

### 검색 정확도 조절
```env
CHUNK_SIZE=1500        # 더 큰 컨텍스트
TOP_K_RESULTS=10       # 더 많은 문서 검색
```

### GUI 테마 변경
`GUI/app.py`의 CSS 스타일 수정

## 🐛 알려진 이슈

1. **큰 데이터셋**: 10만 행 이상의 데이터는 초기 로딩이 오래 걸릴 수 있음
2. **메모리**: 최소 4GB RAM 권장
3. **OpenAI 요금**: GPT-4 사용 시 API 비용 발생

## 🔄 업데이트 로그

### v1.0.0 (2024-12-31)
- 초기 릴리스
- RAG 시스템 구현
- Streamlit GUI 추가
- FastAPI 백엔드 완성

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 아모레퍼시픽 공모전 목적으로 제작되었습니다.

## 👥 제작자

Viewtic 팀원 일동 - khs10049731@gmail.com

## 🙏 감사의 말

- OpenAI GPT-4
- LangChain Community
- FastAPI Team
- Streamlit Team

## 📞 문의

문제가 있거나 제안사항이 있으시면 이슈를 등록해주세요.

---

**Made with ❤️ for better skincare**
