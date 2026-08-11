"""
스킨케어 카테고리별 기대치 트렌드 시각화 (인터랙티브 GUI)
- 카테고리 선택 기능 (리스트에서 클릭)
- 막대그래프와 점선그래프를 같은 그래프에 표시 (dual y-axis)
- 2024년도부터 데이터 표시
- 실시간 업데이트 지원
"""
# 각 카테고리 그래프 생성 GUI
import json
import matplotlib.pyplot as plt
from matplotlib.widgets import RadioButtons
from matplotlib.ticker import MaxNLocator
import numpy as np
from collections import defaultdict
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import time
import os

# 한글 폰트 설정 (macOS)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# 데이터 로드
DATA_FILE = "data/skincare_category_expectation_trends_quarterly.json"

# 카테고리 매핑 (영문 -> 한글)
CATEGORY_MAPPING = {
    "Toner": "토너",
    "Essence & Serum": "에센스&세럼",
    "Face Mist": "face mist",
    "Cream": "크림",
    "Cleansing Foams": "클랜징폼",
    "Cleansing Balms & Oils": "클랜징밤&오일",
    "Makeup Remover": "메이크업리무버",
    "Spot Care": "spot care",
    "Moisturizer": "Moisturizer"
}

# Aspect 매핑 (영문 -> 한글)
ASPECT_MAPPING = {
    "effectiveness": "효과",
    "irritation": "자극",
    "texture": "제형",
    "absorption": "흡수력",
    "moisture": "보습력"
}

# Aspect 색상 설정
ASPECT_COLORS = {
    "effectiveness": "#2E86AB",
    "irritation": "#A23B72",
    "texture": "#F18F01",
    "absorption": "#C73E1D",
    "moisture": "#6A994E"
}

# Aspect 마커 스타일
ASPECT_MARKERS = {
    "effectiveness": "o",
    "irritation": "s",
    "texture": "^",
    "absorption": "D",
    "moisture": "v"
}

def load_data(file_path):
    """JSON 데이터 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_quarter(quarter_str):
    """분기 문자열을 datetime으로 변환"""
    year, q = quarter_str.split('Q')
    month = (int(q) - 1) * 3 + 1
    return datetime(int(year), month, 1)

def filter_quarters_from_2024(quarters_list):
    """2024년부터의 분기만 필터링"""
    filtered = []
    for q in quarters_list:
        year = int(q.split('Q')[0])
        if year >= 2024:
            filtered.append(q)
    return filtered

def extract_category_data(data, category_name):
    """특정 카테고리의 데이터 추출"""
    category_data = data['category_expectation_scores'].get(category_name, {})
    
    aspect_data = defaultdict(dict)
    aspect_review_counts = defaultdict(dict)
    
    for quarter, quarter_data in category_data.items():
        # 2024년부터만 필터링
        if int(quarter.split('Q')[0]) < 2024:
            continue
            
        for aspect, aspect_info in quarter_data.items():
            if aspect in ASPECT_MAPPING:
                score = aspect_info.get('expectation_score', 0)
                review_count = aspect_info.get('total_review_count', 0)
                aspect_data[aspect][quarter] = score
                aspect_review_counts[aspect][quarter] = review_count
    
    return aspect_data, aspect_review_counts

def format_quarter(dt):
    """datetime을 분기 문자열로 변환"""
    quarter = (dt.month - 1) // 3 + 1
    return f"{dt.year}Q{quarter}"

class SkincareDashboard:
    def __init__(self, data):
        self.data = data
        self.current_category = None
        self.current_aspect = "effectiveness"
        # ax2는 setup_ui에서 None으로 초기화됨
        
        # 사용 가능한 카테고리 가져오기
        self.available_categories = [
            cat for cat in CATEGORY_MAPPING.keys()
            if cat in data['category_expectation_scores']
        ]
        
        # 첫 번째 카테고리를 기본으로 선택
        if self.available_categories:
            self.current_category = self.available_categories[0]
        
        self.setup_ui()
        self.update_plot()
        
    def setup_ui(self):
        """UI 설정"""
        # 메인 figure 생성
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle('스킨케어 카테고리별 기대치 트렌드', 
                         fontsize=18, fontweight='bold', y=0.98)
        
        # 그래프 영역 (좌측 큰 영역)
        self.ax_main = plt.subplot2grid((1, 5), (0, 1), colspan=4, fig=self.fig)
        # 초기에는 ax2가 없으므로 None으로 설정
        self.ax2 = None
        
        # 카테고리 선택 라디오 버튼 영역 (좌측)
        self.ax_radio_category = plt.axes([0.02, 0.3, 0.12, 0.5], facecolor='lightgray')
        category_labels = [CATEGORY_MAPPING.get(cat, cat) for cat in self.available_categories]
        self.radio_category = RadioButtons(self.ax_radio_category, category_labels)
        self.radio_category.on_clicked(self.on_category_selected)
        
        # Aspect 선택 라디오 버튼 영역 (좌측 상단)
        self.ax_radio_aspect = plt.axes([0.02, 0.8, 0.12, 0.15], facecolor='lightgray')
        aspect_labels = [ASPECT_MAPPING[aspect] for aspect in ASPECT_MAPPING.keys()]
        self.radio_aspect = RadioButtons(self.ax_radio_aspect, aspect_labels, active=0)
        self.radio_aspect.on_clicked(self.on_aspect_selected)
        
        # 라벨 추가
        self.fig.text(0.08, 0.96, '측면 선택', fontsize=12, fontweight='bold', ha='center')
        self.fig.text(0.08, 0.28, '카테고리 선택', fontsize=12, fontweight='bold', ha='center')
        
    def on_category_selected(self, label):
        """카테고리 선택 시 호출"""
        # 한글 레이블을 영문 카테고리로 변환
        for cat, kor_name in CATEGORY_MAPPING.items():
            if kor_name == label and cat in self.available_categories:
                self.current_category = cat
                break
        self.update_plot()
        
    def on_aspect_selected(self, label):
        """Aspect 선택 시 호출"""
        # 한글 레이블을 영문 aspect로 변환
        for aspect, kor_name in ASPECT_MAPPING.items():
            if kor_name == label:
                self.current_aspect = aspect
                break
        self.update_plot()
        
    def update_plot(self):
        """그래프 업데이트"""
        if not self.current_category:
            return
            
        # 기존 두 번째 축 완전히 제거
        if self.ax2 is not None:
            self.ax2.clear()  # 먼저 클리어
            self.ax2.remove()  # 제거
            self.fig.canvas.draw_idle()  # 화면 갱신
            self.ax2 = None
        
        # 메인 축 클리어
        self.ax_main.clear()
        
        # 카테고리 데이터 추출
        aspect_data, aspect_review_counts = extract_category_data(self.data, self.current_category)
        
        if not aspect_data or self.current_aspect not in aspect_data:
            self.ax_main.text(0.5, 0.5, 
                            f'{CATEGORY_MAPPING.get(self.current_category, self.current_category)}\n데이터 없음',
                            ha='center', va='center', transform=self.ax_main.transAxes,
                            fontsize=16, fontweight='bold')
            self.ax_main.set_xticks([])
            self.ax_main.set_yticks([])
            plt.draw()
            return
        
        # 해당 aspect의 분기와 점수 추출
        quarter_scores = aspect_data[self.current_aspect]
        aspect_reviews = aspect_review_counts.get(self.current_aspect, {})
        
        # 분기 정렬 (2024년부터만)
        sorted_quarters = sorted(quarter_scores.keys(), key=parse_quarter)
        sorted_quarters = filter_quarters_from_2024(sorted_quarters)
        
        if not sorted_quarters:
            self.ax_main.text(0.5, 0.5, '2024년 이후 데이터가 없습니다.',
                            ha='center', va='center', transform=self.ax_main.transAxes,
                            fontsize=16)
            plt.draw()
            return
        
        quarters_dt = [parse_quarter(q) for q in sorted_quarters]
        scores = [quarter_scores[q] for q in sorted_quarters]
        review_values = [aspect_reviews.get(q, 0) for q in sorted_quarters]
        
        # Dual y-axis 설정
        self.ax2 = self.ax_main.twinx()  # 두 번째 y축 (리뷰 수용)
        
        # 막대 그래프 (리뷰 수) - 두 번째 y축
        color_bar = ASPECT_COLORS[self.current_aspect]
        # 막대 그래프 width 계산 (분기 간격의 약 60%로 설정하여 겹치지 않도록)
        if len(quarters_dt) > 1:
            # 분기 간격 계산
            quarter_interval = (quarters_dt[1] - quarters_dt[0]).days
            bar_width_days = int(quarter_interval * 0.6)  # 분기 간격의 60%
        else:
            bar_width_days = 45  # 기본값
        bars = self.ax2.bar(quarters_dt, review_values,
                      color=color_bar, alpha=0.3,
                      width=bar_width_days,
                      edgecolor='black', linewidth=1,
                      label='리뷰 수', zorder=1)
        
        # 막대 위에 값 표시
        for bar, count in zip(bars, review_values):
            if count > 0:
                height = bar.get_height()
                self.ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{count}',
                        ha='center', va='bottom',
                        fontsize=10, fontweight='bold')
        
        # 선 그래프 (기대치) - 첫 번째 y축
        color_line = ASPECT_COLORS[self.current_aspect]
        line = self.ax_main.plot(quarters_dt, scores,
                                color=color_line,
                                marker=ASPECT_MARKERS[self.current_aspect],
                                label=ASPECT_MAPPING[self.current_aspect],
                                linewidth=3,
                                markersize=12,
                                alpha=0.9,
                                zorder=3)
        
        # 점 표시
        self.ax_main.scatter(quarters_dt, scores,
                            color=color_line,
                            s=200,
                            zorder=5,
                            alpha=0.9,
                            edgecolors='white',
                            linewidths=2.5)
        
        # 점에 값 표시
        for dt, score in zip(quarters_dt, scores):
            self.ax_main.annotate(f'{score:.3f}',
                                (dt, score),
                                textcoords="offset points",
                                xytext=(0, 20),
                                ha='center',
                                fontsize=11,
                                fontweight='bold',
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # 그래프 스타일링
        category_name = CATEGORY_MAPPING.get(self.current_category, self.current_category)
        aspect_name = ASPECT_MAPPING[self.current_aspect]
        self.ax_main.set_title(f'{category_name} - {aspect_name}', 
                              fontsize=16, fontweight='bold', pad=20)
        
        # X축 설정 (분기 간격 넓히기)
        if len(quarters_dt) > 1:
            x_min = quarters_dt[0]
            x_max = quarters_dt[-1]
            x_range = (x_max - x_min).days
            # 넓은 여유 공간 (약 30%)
            padding = timedelta(days=int(x_range * 0.15))
            xlim_min = x_min - padding
            xlim_max = x_max + padding
            self.ax_main.set_xlim(xlim_min, xlim_max)
            self.ax2.set_xlim(xlim_min, xlim_max)  # 두 번째 축도 같은 범위 설정
        else:
            # 데이터가 하나만 있을 경우
            if quarters_dt:
                x_center = quarters_dt[0]
                padding = timedelta(days=90)
                self.ax_main.set_xlim(x_center - padding, x_center + padding)
                self.ax2.set_xlim(x_center - padding, x_center + padding)
        
        # X축 레이블 (첫 번째 축에만)
        self.ax_main.set_xticks(quarters_dt)
        self.ax_main.set_xticklabels([format_quarter(dt) for dt in quarters_dt],
                                     rotation=45, ha='right', fontsize=12, fontweight='bold')
        self.ax_main.set_xlabel('분기', fontsize=14, fontweight='bold')
        self.ax2.set_xticks([])  # 두 번째 축의 x축 레이블 제거
        
        # 첫 번째 y축 (기대치)
        if scores:
            y_min = min(scores)
            y_max = max(scores)
            if y_min != y_max:
                y_range = y_max - y_min
                self.ax_main.set_ylim(y_min - y_range * 0.2, y_max + y_range * 0.2)
            else:
                self.ax_main.set_ylim(y_min - 0.1, y_max + 0.1)
        
        # y축 tick 개수 제한 (겹침 방지)
        self.ax_main.yaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
        self.ax_main.set_ylabel('기대치', fontsize=14, fontweight='bold', color=color_line)
        self.ax_main.tick_params(axis='y', labelcolor=color_line, labelsize=11)
        self.ax_main.grid(True, alpha=0.3, linestyle='--', zorder=2)
        self.ax_main.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5, zorder=2)
        
        # 두 번째 y축 (리뷰 수)
        if review_values:
            max_reviews = max(review_values) if max(review_values) > 0 else 1
            self.ax2.set_ylim(0, max_reviews * 1.2)
        
        # y축 tick 개수 제한 (겹침 방지)
        self.ax2.yaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
        self.ax2.set_ylabel('리뷰 수', fontsize=14, fontweight='bold', color=color_bar)
        self.ax2.tick_params(axis='y', labelcolor=color_bar, labelsize=11)
        
        # 범례
        lines1, labels1 = self.ax_main.get_legend_handles_labels()
        lines2, labels2 = self.ax2.get_legend_handles_labels()
        self.ax_main.legend(lines1 + lines2, labels1 + labels2,
                           loc='upper left', fontsize=11, framealpha=0.9)
        
        plt.tight_layout(rect=[0.16, 0, 1, 0.96])
        plt.draw()
        
    def update_data(self, new_data):
        """데이터 업데이트"""
        self.data = new_data
        self.update_plot()

def main():
    """메인 함수"""
    print("="*60)
    print("📊 스킨케어 기대치 트렌드 시각화 대시보드")
    print("="*60)
    
    # 인터랙티브 모드 활성화
    plt.ion()
    
    # 데이터 로드
    print(f"\n📂 데이터 로딩: {DATA_FILE}")
    data = load_data(DATA_FILE)
    print(f"✅ {len(data['category_expectation_scores'])}개 카테고리 로드 완료\n")
    
    # 대시보드 생성
    dashboard = SkincareDashboard(data)
    
    # 파일 수정 시간 추적
    last_modified = os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else 0
    
    print("✅ 대시보드가 실행되었습니다!")
    print("   - 좌측에서 카테고리와 측면을 선택하세요")
    print("   - 데이터 파일이 업데이트되면 자동으로 갱신됩니다")
    print("   - 종료하려면 창을 닫거나 Ctrl+C를 누르세요\n")
    
    try:
        while True:
            # 모든 figure가 닫혔는지 확인
            if not plt.fignum_exists(dashboard.fig.number):
                print("\n창이 닫혔습니다. 종료합니다.")
                break
            
            # 파일 변경 감지
            if os.path.exists(DATA_FILE):
                current_modified = os.path.getmtime(DATA_FILE)
                if current_modified > last_modified:
                    print(f"\n🔄 데이터 파일이 업데이트되었습니다. 그래프를 갱신합니다...")
                    try:
                        data = load_data(DATA_FILE)
                        dashboard.update_data(data)
                        last_modified = current_modified
                        print("✅ 그래프 갱신 완료!\n")
                    except Exception as e:
                        print(f"❌ 그래프 갱신 중 오류 발생: {e}\n")
            
            plt.pause(2)
            
    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다...")
    finally:
        plt.ioff()
        plt.close('all')
        print("✅ 종료되었습니다.")

"""-------------------- 미래 예측 그래프 / 12-27 (우석,동건)------------------------"""
import matplotlib.pyplot as plt
import json

# 1. 데이터 로드 (우석이가 준 파일)
with open('skincare_category_expectation_trends_quarterly.json', 'r') as f:
    data = json.load(f)

def get_forecast(category, aspect):
    # 과거 데이터 추출
    scores_dict = data['category_expectation_scores'][category]
    sorted_qs = sorted(scores_dict.keys())[-4:] # 최근 4분기
    
    history_x = sorted_qs
    history_y = [scores_dict[q][aspect]['expectation_score'] for q in sorted_qs]
    
    # --- LLM 혹은 수학적 예측 로직 ---
    # 실제로는 여기서 GPT/Gemini에게 "이 추세면 다음은 몇 점일까?"라고 물어봄
    last_score = history_y[-1]
    last_delta = data['category_expectation_score_deltas'][category][sorted_qs[-1]][aspect]
    
    # 간단한 예측: 현재 변화량의 80%만 다음 분기에 반영된다고 가정 (감쇠 모델)
    predicted_score = last_score + (last_delta * 0.8)
    # --------------------------------
    
    return history_x, history_y, "2026Q1", predicted_score

# 2. 그래프 그리기
category, aspect = "Toner", "moisture"
hx, hy, fx, fy = get_forecast(category, aspect)

plt.figure(figsize=(10, 6))

# (1) 과거 데이터: 실선
plt.plot(hx, hy, marker='o', linestyle='-', color='blue', label='Actual Data')

# (2) 미래 예측: 점선 (마지막 실제 데이터 지점부터 시작)
plt.plot([hx[-1], fx], [hy[-1], fy], marker='D', linestyle='--', color='red', label='LLM Forecast')

# 그래프 꾸미기
plt.title(f"[{category}] {aspect} - 미래 트렌드 예측", fontsize=15)
plt.ylabel("기대 점수 (Expectation Score)")
plt.grid(True, alpha=0.3)
plt.legend()

plt.savefig('forecast_trend.png')
print(f"🚀 {category}의 다음 분기 예측 점수: {fy:.4f}")

if __name__ == "__main__":
    main()

