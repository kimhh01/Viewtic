import pandas as pd
import re
import json
import os
from collections import Counter
from datetime import datetime

# =========================
# 1. 올리브영 데이터 로드 및 전처리
# =========================
print("="*70)
print("📂 STEP 1: 올리브영 데이터 로딩 중...")
print("="*70)

oliveyoung_file = "AI model/data/skincare_reviews_complete.csv"

try:
    oy_df = pd.read_csv(oliveyoung_file, encoding='utf-8-sig')
    print(f"✅ 올리브영 데이터 로드 완료: {len(oy_df)}개 행")
    print(f"   컬럼: {list(oy_df.columns)}")
except FileNotFoundError:
    print(f"❌ 파일을 찾을 수 없습니다: {oliveyoung_file}")
    oy_df = pd.DataFrame()

# =========================
# 2. Reddit 데이터 로드 및 전처리
# =========================
print("\n" + "="*70)
print("📂 STEP 2: Reddit 데이터 로딩 중...")
print("="*70)

reddit_file = "아모레퍼시픽 레딧 크롤링/data/reddit_crawling_result.csv"

try:
    reddit_df = pd.read_csv(reddit_file, encoding='utf-8-sig')
    print(f"✅ Reddit 데이터 로드 완료: {len(reddit_df)}개 행")
    print(f"   컬럼: {list(reddit_df.columns)}")
except FileNotFoundError:
    print(f"❌ 파일을 찾을 수 없습니다: {reddit_file}")
    reddit_df = pd.DataFrame()

# =========================
# 3. 공통 전처리 함수 정의
# =========================
print("\n" + "="*70)
print("🔧 STEP 3: 공통 전처리 함수 정의")
print("="*70)

def clean_product_name(name):
    """제품명 정리"""
    if pd.isna(name):
        return name
    cleaned = re.sub(r'[★☆]+', '', name)
    cleaned = re.sub(r'\*+[^*]+\*+', '', cleaned)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def get_quarter_from_date(date):
    """날짜로부터 분기 문자열 생성"""
    if pd.isna(date):
        return None
    quarter = (date.month - 1) // 3 + 1
    return f"{date.year}Q{quarter}"

def is_valid_review(text):
    """리뷰 유효성 검증"""
    if pd.isna(text) or len(str(text).strip()) < 10:
        return False, "too_short"
    
    text = str(text)
    if re.search(r'(.)\1{5,}', text):
        return False, "character_repetition"
    
    alpha_chars = len(re.findall(r'[a-zA-Z]', text))
    total_chars = len(text.replace(' ', ''))
    if total_chars > 0 and alpha_chars / total_chars < 0.3:
        return False, "low_alpha_ratio"
    
    words = text.split()
    if len(words) < 3:
        return False, "too_few_words"
    
    return True, "valid"

# Aspect 신호 키워드 사전
ASPECT_SIGNALS = {
    'texture': {
        'positive': ['smooth', 'silky', 'soft', 'lightweight', 'velvety', 'creamy', 'luxurious'],
        'negative': ['sticky', 'greasy', 'heavy', 'thick', 'oily', 'tacky', 'gooey', 'slimy']
    },
    'absorption': {
        'positive': ['absorbs', 'quickly', 'fast', 'instantly', 'penetrates', 'sinks'],
        'negative': ['slow', 'sits', 'surface', 'takes forever', 'doesn\'t absorb']
    },
    'moisture': {
        'positive': ['moisturizing', 'hydrating', 'hydrated', 'plump', 'dewy', 'nourishing', 'supple'],
        'negative': ['dry', 'drying', 'dehydrated', 'tight', 'stripped']
    },
    'effectiveness': {
        'positive': ['works', 'effective', 'results', 'improved', 'visible', 'noticeable', 'helped', 'amazing'],
        'negative': ['nothing', 'no effect', 'didn\'t work', 'useless', 'waste', 'no results', 'no difference']
    },
    'irritation': {
        'positive': ['gentle', 'mild', 'soothing', 'calming', 'no irritation', 'comfortable'],
        'negative': ['irritating', 'burning', 'stinging', 'redness', 'itchy', 'sensitive', 'reaction', 'breakout']
    },
    'scent': {
        'positive': ['nice scent', 'pleasant', 'smells good', 'love the smell', 'fragrance'],
        'negative': ['strong smell', 'overpowering', 'chemical smell', 'hate the scent', 'stinks']
    }
}

def extract_aspect_signals(text):
    """Aspect별 긍정/부정 신호 추출"""
    if pd.isna(text):
        return {}
    
    text_lower = str(text).lower()
    signals = {}
    
    for aspect, keywords in ASPECT_SIGNALS.items():
        positive_found = [kw for kw in keywords['positive'] if kw in text_lower]
        negative_found = [kw for kw in keywords['negative'] if kw in text_lower]
        
        if positive_found or negative_found:
            signals[aspect] = {
                'positive': positive_found,
                'negative': negative_found,
                'has_conflict': len(positive_found) > 0 and len(negative_found) > 0
            }
    
    return signals

# =========================
# 4. 올리브영 데이터 전처리
# =========================
if not oy_df.empty:
    print("\n" + "="*70)
    print("🧹 STEP 4: 올리브영 데이터 전처리")
    print("="*70)
    
    # 제품명 정리
    oy_df['product_name'] = oy_df['product_name'].apply(clean_product_name)
    
    # 날짜 처리 (timezone 제거)
    if 'review_date' not in oy_df.columns and 'review_month' in oy_df.columns:
        oy_df['review_date'] = pd.to_datetime(oy_df['review_month'] + '-01', errors='coerce')
    else:
        oy_df['review_date'] = pd.to_datetime(oy_df['review_date'], errors='coerce')
    
    # timezone 제거 (tz-naive로 통일)
    if oy_df['review_date'].dt.tz is not None:
        oy_df['review_date'] = oy_df['review_date'].dt.tz_localize(None)
    
    oy_df['review_quarter'] = oy_df['review_date'].apply(get_quarter_from_date)
    
    # 유효성 검증
    oy_df['is_valid'], oy_df['noise_type'] = zip(*oy_df['review_text'].apply(is_valid_review))
    oy_valid = oy_df[oy_df['is_valid']].copy()
    
    # 신호 추출
    oy_valid['aspect_signals'] = oy_valid['review_text'].apply(extract_aspect_signals)
    oy_valid['source'] = 'oliveyoung'
    
    print(f"✅ 올리브영 유효 리뷰: {len(oy_valid)}개 (제거: {len(oy_df) - len(oy_valid)}개)")

# =========================
# 5. Reddit 데이터 전처리
# =========================
if not reddit_df.empty:
    print("\n" + "="*70)
    print("🧹 STEP 5: Reddit 데이터 전처리")
    print("="*70)
    
    # 제품명 정리 (keyword 컬럼 사용)
    reddit_df['product_name'] = reddit_df['keyword'].apply(clean_product_name)
    
    # 날짜 처리 (comment_time_iso 또는 post_time_iso)
    reddit_df['review_date'] = pd.to_datetime(
        reddit_df['comment_time_iso'].fillna(reddit_df['post_time_iso']), 
        errors='coerce',
        utc=True  # ISO 형식 날짜를 UTC로 파싱
    )
    
    # timezone 제거 (tz-naive로 통일)
    if reddit_df['review_date'].dt.tz is not None:
        reddit_df['review_date'] = reddit_df['review_date'].dt.tz_localize(None)
    
    reddit_df['review_quarter'] = reddit_df['review_date'].apply(get_quarter_from_date)
    
    # 텍스트 통합 (댓글이 있으면 댓글, 없으면 본문)
    reddit_df['review_text'] = reddit_df.apply(
        lambda row: row['comment_text'] if pd.notna(row['comment_text']) and row['comment_text'].strip() 
        else row['post_body'] if pd.notna(row['post_body']) else '', 
        axis=1
    )
    
    # 유효성 검증
    reddit_df['is_valid'], reddit_df['noise_type'] = zip(*reddit_df['review_text'].apply(is_valid_review))
    reddit_valid = reddit_df[reddit_df['is_valid']].copy()
    
    # 신호 추출
    reddit_valid['aspect_signals'] = reddit_valid['review_text'].apply(extract_aspect_signals)
    reddit_valid['source'] = 'reddit'
    reddit_valid['subreddit'] = reddit_valid['subreddit']
    reddit_valid['relevance_score'] = reddit_valid['relevance_score']
    
    print(f"✅ Reddit 유효 리뷰: {len(reddit_valid)}개 (제거: {len(reddit_df) - len(reddit_valid)}개)")

# =========================
# 6. 데이터 통합
# =========================
print("\n" + "="*70)
print("🔗 STEP 6: 데이터 통합")
print("="*70)

# 공통 컬럼 정의
common_columns = [
    'product_name', 'review_text', 'review_date', 'review_quarter',
    'aspect_signals', 'source'
]

integrated_data = []

# 올리브영 데이터 추가
if not oy_df.empty and 'oy_valid' in locals():
    oy_subset = oy_valid[common_columns + ['product_category', 'star_score', 'skin_type', 'skin_concerns']].copy()
    oy_subset['platform_specific'] = oy_subset.apply(
        lambda row: {
            'category': row.get('product_category'),
            'rating': row.get('star_score'),
            'skin_type': row.get('skin_type'),
            'skin_concerns': row.get('skin_concerns')
        }, axis=1
    )
    integrated_data.append(oy_subset[common_columns + ['platform_specific']])
    print(f"  ✓ 올리브영: {len(oy_subset)}개 리뷰 추가")

# Reddit 데이터 추가
if not reddit_df.empty and 'reddit_valid' in locals():
    reddit_subset = reddit_valid[common_columns + ['subreddit', 'relevance_score', 'post_url']].copy()
    reddit_subset['platform_specific'] = reddit_subset.apply(
        lambda row: {
            'subreddit': row.get('subreddit'),
            'relevance_score': row.get('relevance_score'),
            'post_url': row.get('post_url')
        }, axis=1
    )
    integrated_data.append(reddit_subset[common_columns + ['platform_specific']])
    print(f"  ✓ Reddit: {len(reddit_subset)}개 리뷰 추가")

if integrated_data:
    integrated_df = pd.concat(integrated_data, ignore_index=True)
    print(f"\n✅ 통합 완료: 총 {len(integrated_df)}개 리뷰")
    print(f"   - 올리브영: {len(integrated_df[integrated_df['source']=='oliveyoung'])}개")
    print(f"   - Reddit: {len(integrated_df[integrated_df['source']=='reddit'])}개")
else:
    print("❌ 통합할 데이터가 없습니다.")
    integrated_df = pd.DataFrame()

# =========================
# 7. 제품별 통합 분석
# =========================
if not integrated_df.empty:
    print("\n" + "="*70)
    print("📊 STEP 7: 제품별 통합 분석")
    print("="*70)
    
    products_integrated = []
    
    for product_name in sorted(integrated_df['product_name'].unique()):
        product_df = integrated_df[integrated_df['product_name'] == product_name]
        
        # 소스별 분포
        source_dist = product_df['source'].value_counts().to_dict()
        
        # 분기별 트렌드 (통합)
        quarterly_trends = {}
        for quarter in sorted(product_df['review_quarter'].dropna().unique()):
            quarter_df = product_df[product_df['review_quarter'] == quarter]
            
            quarter_signals = {}
            for aspect in ASPECT_SIGNALS.keys():
                positive_all = []
                negative_all = []
                
                for signals in quarter_df['aspect_signals']:
                    if aspect in signals:
                        positive_all.extend(signals[aspect]['positive'])
                        negative_all.extend(signals[aspect]['negative'])
                
                if positive_all or negative_all:
                    quarter_signals[aspect] = {
                        'positive_count': len(positive_all),
                        'negative_count': len(negative_all),
                        'top_positive': dict(Counter(positive_all).most_common(3)),
                        'top_negative': dict(Counter(negative_all).most_common(3))
                    }
            
            quarterly_trends[quarter] = {
                'review_count': len(quarter_df),
                'sources': quarter_df['source'].value_counts().to_dict(),
                'signals': quarter_signals
            }
        
        # Aspect 신호 요약 (통합)
        aspect_summary = {}
        for aspect in ASPECT_SIGNALS.keys():
            positive_all = []
            negative_all = []
            
            for signals in product_df['aspect_signals']:
                if aspect in signals:
                    positive_all.extend(signals[aspect]['positive'])
                    negative_all.extend(signals[aspect]['negative'])
            
            if positive_all or negative_all:
                aspect_summary[aspect] = {
                    'positive_mentions': dict(Counter(positive_all).most_common(10)),
                    'negative_mentions': dict(Counter(negative_all).most_common(10)),
                    'positive_count': len(positive_all),
                    'negative_count': len(negative_all)
                }
        
        # 소스별 차이 분석
        source_comparison = {}
        for source in ['oliveyoung', 'reddit']:
            source_df = product_df[product_df['source'] == source]
            if len(source_df) > 0:
                source_signals = {}
                for aspect in ASPECT_SIGNALS.keys():
                    neg_all = []
                    for signals in source_df['aspect_signals']:
                        if aspect in signals:
                            neg_all.extend(signals[aspect]['negative'])
                    if neg_all:
                        source_signals[aspect] = dict(Counter(neg_all).most_common(5))
                
                source_comparison[source] = {
                    'review_count': len(source_df),
                    'top_complaints': source_signals
                }
        
        product_info = {
            'product_name': product_name,
            'total_reviews': len(product_df),
            'source_distribution': source_dist,
            'quarterly_trends': quarterly_trends,
            'aspect_summary': aspect_summary,
            'source_comparison': source_comparison,
            'sample_reviews': product_df[['source', 'review_text', 'review_quarter']].head(10).to_dict('records')
        }
        
        products_integrated.append(product_info)
        
        print(f"\n  ✓ {product_name}")
        print(f"    - 총 리뷰: {len(product_df)}개")
        print(f"    - 출처: {source_dist}")

# =========================
# 8. JSON 직렬화를 위한 변환
# =========================
def convert_to_json_serializable(obj):
    """pandas/numpy 타입을 JSON 직렬화 가능한 타입으로 변환"""
    if isinstance(obj, (pd.Timestamp, pd.DatetimeTZDtype)):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, (pd.Series, pd.Index)):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif pd.isna(obj):
        return None
    elif isinstance(obj, (bool, int, float, str)):
        return obj
    else:
        return str(obj)

# =========================
# 9. 최종 데이터 구조 생성
# =========================
if not integrated_df.empty:
    print("\n" + "="*70)
    print("💾 STEP 8: 최종 데이터 구조 생성")
    print("="*70)
    
    final_integrated_data = {
        'metadata': {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_sources': ['Olive Young', 'Reddit'],
            'total_products': len(products_integrated),
            'total_reviews': len(integrated_df),
            'source_breakdown': integrated_df['source'].value_counts().to_dict(),
            'date_range': {
                'earliest': str(integrated_df['review_date'].min()) if pd.notna(integrated_df['review_date'].min()) else None,
                'latest': str(integrated_df['review_date'].max()) if pd.notna(integrated_df['review_date'].max()) else None
            },
            'quarters_covered': sorted([str(q) for q in integrated_df['review_quarter'].dropna().unique()])
        },
        
        'signal_definitions': {
            'aspects': list(ASPECT_SIGNALS.keys()),
            'aspect_keywords': {
                aspect: {
                    'positive': keywords['positive'],
                    'negative': keywords['negative']
                }
                for aspect, keywords in ASPECT_SIGNALS.items()
            }
        },
        
        'products': products_integrated,
        
        'analysis_guide': {
            'cross_platform_questions': [
                'Are there different complaints between Olive Young and Reddit users?',
                'Which aspects are consistently problematic across both platforms?',
                'Do international users (Reddit) have different concerns than Korean users (Olive Young)?'
            ],
            'temporal_analysis': [
                'Which complaints are increasing over quarters?',
                'Are there seasonal patterns in user feedback?',
                'How has product perception changed over time?'
            ],
            'aspect_analysis': [
                'Which aspects have the most negative signals?',
                'Are there conflicting opinions on certain aspects?',
                'What are the top improvement priorities based on user feedback?'
            ]
        }
    }
    
    # JSON 직렬화
    final_data_serializable = convert_to_json_serializable(final_integrated_data)
    
    # 저장
    output_file = "AI model/data/integrated_skincare_analysis.json"
    os.makedirs("data", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data_serializable, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 통합 분석 완료!")
    print(f"📁 저장 위치: {output_file}")
    
    # 통합 CSV도 저장
    csv_output = "AI model/data/integrated_reviews.csv"
    integrated_df.to_csv(csv_output, index=False, encoding='utf-8-sig')
    print(f"📁 CSV 저장: {csv_output}")

# =========================
# 10. 최종 요약
# =========================
print("\n" + "="*70)
print("📋 통합 전처리 완료 요약")
print("="*70)

if not integrated_df.empty:
    print(f"\n✅ 데이터 통합 성공:")
    print(f"  • 총 제품 수: {integrated_df['product_name'].nunique()}개")
    print(f"  • 총 리뷰 수: {len(integrated_df)}개")
    print(f"  • 올리브영: {len(integrated_df[integrated_df['source']=='oliveyoung'])}개")
    print(f"  • Reddit: {len(integrated_df[integrated_df['source']=='reddit'])}개")
    print(f"  • 분석 기간: {integrated_df['review_quarter'].min()} ~ {integrated_df['review_quarter'].max()}")
    
    print(f"\n🎯 분석 가능한 인사이트:")
    print(f"  ✓ 플랫폼 간 사용자 피드백 차이")
    print(f"  ✓ 시간대별 제품 만족도 변화")
    print(f"  ✓ 글로벌 vs 로컬 사용자 선호도")
    print(f"  ✓ Aspect별 개선 우선순위")
else:
    print("\n❌ 통합할 데이터가 없습니다. 입력 파일을 확인해주세요.")

print("\n" + "="*70)