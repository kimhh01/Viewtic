import sys
import requests
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QSplitter,
    QListWidget, QMessageBox, QSpinBox, QDoubleSpinBox, QGroupBox,
    QDialog, QDialogButtonBox, QFormLayout, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor

# =========================
# API 통신 스레드
# =========================
class APIWorkerThread(QThread):
    """백그라운드에서 API 호출하는 스레드"""
    response_ready = pyqtSignal(str, list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_url, user_input, conversation_history, n_results=5, temperature=0.7):
        super().__init__()
        self.api_url = api_url
        self.user_input = user_input
        self.conversation_history = conversation_history
        self.n_results = n_results
        self.temperature = temperature
    
    def run(self):
        try:
            # API 요청 데이터 구성
            payload = {
                "question": self.user_input,
                "n_results": self.n_results,
                "temperature": self.temperature,
                "conversation_history": self.conversation_history
            }
            
            # POST 요청
            response = requests.post(
                f"{self.api_url}/chat",
                json=payload,
                timeout=30
            )
            
            # 응답 확인
            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                sources = data.get('sources', [])
                self.response_ready.emit(answer, sources)
            else:
                self.error_occurred.emit(
                    f"서버 오류 (코드: {response.status_code})\n{response.text}"
                )
                
        except requests.exceptions.Timeout:
            self.error_occurred.emit("서버 응답 시간 초과 (30초)")
        except requests.exceptions.ConnectionError:
            self.error_occurred.emit(
                "서버에 연결할 수 없습니다.\n서버 주소와 상태를 확인해주세요."
            )
        except Exception as e:
            self.error_occurred.emit(f"오류 발생: {str(e)}")

# =========================
# 서버 설정 다이얼로그
# =========================
class ServerSettingsDialog(QDialog):
    """서버 주소 설정 다이얼로그"""
    
    def __init__(self, current_url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("서버 설정")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QFormLayout()
        
        # 서버 URL 입력
        self.url_input = QLineEdit(current_url)
        self.url_input.setPlaceholderText("http://localhost:8000")
        layout.addRow("서버 주소:", self.url_input)
        
        # 설명
        info_label = QLabel(
            "FastAPI 서버의 주소를 입력하세요.\n"
            "예: http://localhost:8000 또는 http://192.168.0.10:8000"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addRow(info_label)
        
        # 버튼
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
        self.setLayout(layout)
    
    def get_url(self):
        """입력된 URL 반환"""
        url = self.url_input.text().strip()
        # 끝의 슬래시 제거
        return url.rstrip('/')

# =========================
# 메인 GUI 클라이언트
# =========================
class SkincareChatClientGUI(QMainWindow):
    """FastAPI 서버와 통신하는 채팅 클라이언트 GUI"""
    
    def __init__(self):
        super().__init__()
        self.api_url = "http://localhost:8000"  # 기본 서버 주소
        self.conversation_history = []
        self.worker_thread = None
        self.sources = []
        
        self.init_ui()
        self.check_server_connection()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("🧴 스킨케어 리뷰 AI 분석 시스템 (클라이언트)")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 왼쪽: 대화 영역
        chat_widget = self.create_chat_area()
        
        # 오른쪽: 설정 및 예시
        settings_widget = self.create_settings_area()
        
        # 스플리터로 분할
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(chat_widget)
        splitter.addWidget(settings_widget)
        splitter.setSizes([800, 400])
        
        main_layout.addWidget(splitter)
        
        # 상태바
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.update_status_bar("서버 연결 확인 중...")
        
        # 스타일 적용
        self.apply_styles()
    
    def create_chat_area(self):
        """채팅 영역 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 타이틀
        title_label = QLabel("💬 AI 분석가와 대화")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 서버 정보
        self.server_info_label = QLabel(f"📡 서버: {self.api_url}")
        self.server_info_label.setStyleSheet(
            "background-color: #e3f2fd; padding: 5px; border-radius: 3px;"
        )
        layout.addWidget(self.server_info_label)
        
        # 채팅 디스플레이
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("맑은 고딕", 10))
        layout.addWidget(self.chat_display)
        
        # 입력 영역
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("질문을 입력하세요... (예: 끈적임 불만이 가장 많은 제품은?)")
        self.input_field.setFont(QFont("맑은 고딕", 10))
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("전송")
        self.send_button.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(100)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # 하단 버튼
        button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("🗑️ 대화 기록 초기화")
        self.clear_button.clicked.connect(self.clear_chat)
        button_layout.addWidget(self.clear_button)
        
        self.stats_button = QPushButton("📊 통계 보기")
        self.stats_button.clicked.connect(self.show_stats)
        button_layout.addWidget(self.stats_button)
        
        self.server_button = QPushButton("⚙️ 서버 설정")
        self.server_button.clicked.connect(self.open_server_settings)
        button_layout.addWidget(self.server_button)
        
        layout.addLayout(button_layout)
        
        return widget
    
    def create_settings_area(self):
        """설정 및 예시 영역 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 설정 그룹
        settings_group = QGroupBox("⚙️ 설정")
        settings_layout = QVBoxLayout()
        settings_group.setLayout(settings_layout)
        
        # 검색 결과 개수
        search_layout = QHBoxLayout()
        search_label = QLabel("검색 데이터 개수:")
        self.n_results_spin = QSpinBox()
        self.n_results_spin.setRange(3, 10)
        self.n_results_spin.setValue(5)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.n_results_spin)
        settings_layout.addLayout(search_layout)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_label = QLabel("창의성 수준:")
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 1.5)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        temp_layout.addWidget(temp_label)
        temp_layout.addWidget(self.temperature_spin)
        settings_layout.addLayout(temp_layout)
        
        layout.addWidget(settings_group)
        
        # 서버 상태 그룹
        status_group = QGroupBox("📡 서버 상태")
        status_layout = QVBoxLayout()
        status_group.setLayout(status_layout)
        
        self.server_status_label = QLabel("연결 확인 중...")
        self.server_status_label.setWordWrap(True)
        status_layout.addWidget(self.server_status_label)
        
        check_button = QPushButton("🔄 연결 확인")
        check_button.clicked.connect(self.check_server_connection)
        status_layout.addWidget(check_button)
        
        layout.addWidget(status_group)
        
        # 예시 질문 그룹
        examples_group = QGroupBox("💡 질문 예시")
        examples_layout = QVBoxLayout()
        examples_group.setLayout(examples_layout)
        
        self.example_list = QListWidget()
        self.example_list.setFont(QFont("맑은 고딕", 9))
        
        # 기본 예시 질문
        default_examples = [
            "끈적임 불만이 가장 많은 제품은?",
            "지성 피부와 건성 피부의 불만 차이는?",
            "최근 분기에 개선된 제품은?",
            "질감 관련 불만이 증가하는 추세인가요?",
            "가장 우선적으로 개선할 부분은?",
            "Product A의 주요 불만사항은?",
            "여름철에 불만이 많은 제품은?",
            "흡수력이 좋다는 평가를 받는 제품은?",
            "민감성 피부에 적합한 제품은?",
            "2024년 Q4의 주요 트렌드는?"
        ]
        
        for question in default_examples:
            self.example_list.addItem(question)
        
        self.example_list.itemDoubleClicked.connect(self.use_example_question)
        examples_layout.addWidget(self.example_list)
        
        use_example_button = QPushButton("선택한 질문 사용")
        use_example_button.clicked.connect(self.use_example_question)
        examples_layout.addWidget(use_example_button)
        
        load_examples_button = QPushButton("🔄 서버에서 예시 불러오기")
        load_examples_button.clicked.connect(self.load_examples_from_server)
        examples_layout.addWidget(load_examples_button)
        
        layout.addWidget(examples_group)
        
        # 도움말
        help_label = QLabel(
            "💡 팁:\n"
            "• FastAPI 서버와 통신합니다\n"
            "• 서버 주소는 '⚙️ 서버 설정'에서 변경\n"
            "• 서버 상태를 확인하세요"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("background-color: #f0f8ff; padding: 10px; border-radius: 5px;")
        layout.addWidget(help_label)
        
        layout.addStretch()
        
        return widget
    
    def apply_styles(self):
        """스타일 적용"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
            QLineEdit {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
    
    def check_server_connection(self):
        """서버 연결 확인"""
        self.update_status_bar("서버 연결 확인 중...")
        
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                vector_loaded = data.get('vector_store_loaded', False)
                
                if status == 'healthy' and vector_loaded:
                    self.server_status_label.setText(
                        "✅ 서버 연결 성공\n"
                        "✅ 벡터 DB 로드됨\n"
                        "준비 완료!"
                    )
                    self.server_status_label.setStyleSheet("color: green;")
                    self.update_status_bar(f"서버 연결됨: {self.api_url}")
                    self.send_button.setEnabled(True)
                    self.input_field.setEnabled(True)
                else:
                    self.server_status_label.setText(
                        f"⚠️  서버 응답: {status}\n"
                        f"벡터 DB: {'로드됨' if vector_loaded else '로드 안됨'}"
                    )
                    self.server_status_label.setStyleSheet("color: orange;")
                    self.update_status_bar("서버 상태 불안정")
            else:
                raise Exception(f"서버 오류 (코드: {response.status_code})")
                
        except requests.exceptions.ConnectionError:
            self.server_status_label.setText(
                "❌ 서버에 연결할 수 없습니다\n"
                f"주소: {self.api_url}\n"
                "서버가 실행 중인지 확인하세요"
            )
            self.server_status_label.setStyleSheet("color: red;")
            self.update_status_bar("서버 연결 실패")
            self.send_button.setEnabled(False)
            self.input_field.setEnabled(False)
            
        except Exception as e:
            self.server_status_label.setText(f"❌ 오류: {str(e)}")
            self.server_status_label.setStyleSheet("color: red;")
            self.update_status_bar("서버 확인 오류")
    
    def open_server_settings(self):
        """서버 설정 다이얼로그 열기"""
        dialog = ServerSettingsDialog(self.api_url, self)
        
        if dialog.exec_() == QDialog.Accepted:
            new_url = dialog.get_url()
            if new_url:
                self.api_url = new_url
                self.server_info_label.setText(f"📡 서버: {self.api_url}")
                self.check_server_connection()
    
    def load_examples_from_server(self):
        """서버에서 예시 질문 불러오기"""
        try:
            response = requests.get(f"{self.api_url}/examples", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                examples = data.get('examples', [])
                
                if examples:
                    self.example_list.clear()
                    for question in examples:
                        self.example_list.addItem(question)
                    
                    QMessageBox.information(
                        self,
                        "성공",
                        f"{len(examples)}개의 예시 질문을 불러왔습니다."
                    )
                else:
                    QMessageBox.warning(self, "경고", "서버에서 예시 질문을 찾을 수 없습니다.")
            else:
                QMessageBox.warning(self, "경고", f"서버 오류 (코드: {response.status_code})")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"예시 불러오기 실패:\n{str(e)}")
    
    def send_message(self):
        """메시지 전송"""
        user_input = self.input_field.text().strip()
        
        if not user_input:
            return
        
        # 사용자 메시지 표시
        self.append_user_message(user_input)
        
        # 입력 필드 초기화
        self.input_field.clear()
        
        # 버튼 비활성화
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # 로딩 메시지
        self.append_system_message("🔍 서버에 요청을 보내는 중...")
        self.update_status_bar("서버 응답 대기 중...")
        
        # 대화 히스토리에 추가
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # API 호출 (백그라운드 스레드)
        self.worker_thread = APIWorkerThread(
            api_url=self.api_url,
            user_input=user_input,
            conversation_history=self.conversation_history,
            n_results=self.n_results_spin.value(),
            temperature=self.temperature_spin.value()
        )
        self.worker_thread.response_ready.connect(self.on_response_ready)
        self.worker_thread.error_occurred.connect(self.on_error)
        self.worker_thread.start()
    
    def on_response_ready(self, response, sources):
        """API 응답 수신"""
        # 로딩 메시지 제거
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        
        # AI 응답 표시
        self.append_ai_message(response)
        
        # 소스 정보 저장
        self.sources = sources
        
        # 소스 정보 표시
        if sources:
            source_text = f"\n📚 참고 데이터 ({len(sources)}개):"
            for i, source in enumerate(sources[:3], 1):
                source_text += f"\n  {i}. [{source.get('type', 'N/A')}] {source.get('product_name', 'N/A')}"
            if len(sources) > 3:
                source_text += f"\n  ... 외 {len(sources)-3}개"
            self.append_system_message(source_text)
        
        # 대화 히스토리에 추가
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # 버튼 활성화
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.update_status_bar("준비")
    
    def on_error(self, error_message):
        """오류 처리"""
        # 로딩 메시지 제거
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        
        self.append_system_message(f"❌ {error_message}")
        
        # 버튼 활성화
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        self.update_status_bar("오류 발생")
    
    def append_user_message(self, message):
        """사용자 메시지 추가"""
        self.chat_display.append(
            f"<div style='background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px;'>"
            f"<b>💬 당신:</b><br>{message}"
            f"</div>"
        )
    
    def append_ai_message(self, message):
        """AI 메시지 추가"""
        formatted_message = message.replace('\n', '<br>')
        self.chat_display.append(
            f"<div style='background-color: #f1f8e9; padding: 10px; border-radius: 10px; margin: 5px;'>"
            f"<b>🤖 AI 분석가:</b><br>{formatted_message}"
            f"</div>"
        )
    
    def append_system_message(self, message):
        """시스템 메시지 추가"""
        formatted_message = message.replace('\n', '<br>')
        self.chat_display.append(
            f"<div style='background-color: #fff3e0; padding: 8px; border-radius: 8px; margin: 5px; text-align: center;'>"
            f"<i>{formatted_message}</i>"
            f"</div>"
        )
    
    def use_example_question(self):
        """예시 질문 사용"""
        current_item = self.example_list.currentItem()
        if current_item:
            question = current_item.text()
            self.input_field.setText(question)
            self.input_field.setFocus()
    
    def clear_chat(self):
        """대화 기록 초기화"""
        reply = QMessageBox.question(
            self,
            "확인",
            "대화 기록을 초기화하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.chat_display.clear()
            self.conversation_history = []
            self.sources = []
            self.append_system_message("🗑️ 대화 기록이 초기화되었습니다.")
    
    def show_stats(self):
        """통계 표시"""
        total_messages = len(self.conversation_history)
        user_messages = total_messages // 2
        
        stats_text = (
            f"총 대화 수: {user_messages}회\n"
            f"총 메시지: {total_messages}개\n"
            f"검색 데이터 개수: {self.n_results_spin.value()}개\n"
            f"창의성 수준: {self.temperature_spin.value()}\n"
            f"서버 주소: {self.api_url}"
        )
        
        if self.sources:
            stats_text += f"\n마지막 응답 소스: {len(self.sources)}개"
        
        QMessageBox.information(self, "📊 세션 통계", stats_text)
    
    def update_status_bar(self, message):
        """상태바 업데이트"""
        self.statusBar.showMessage(message)

# =========================
# 메인 실행
# =========================
def main():
    app = QApplication(sys.argv)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("스킨케어 리뷰 AI 분석 시스템 (클라이언트)")
    app.setOrganizationName("Skincare AI")
    
    # 메인 윈도우 생성
    window = SkincareChatClientGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()