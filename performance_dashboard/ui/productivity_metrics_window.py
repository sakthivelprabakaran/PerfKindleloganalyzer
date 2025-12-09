import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMessageBox,
    QGroupBox, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime


class ProductivityMetricsWindow(QWidget):
    """Admin-facing window to view productivity metrics for all executors"""
    
    def __init__(self, server_url="http://127.0.0.1:8000", auth_token=None, parent=None):
        super().__init__(parent)
        self.server_url = server_url
        self.auth_token = auth_token
        self.headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        
        self.init_ui()
        self.load_data()
        
        # Auto-refresh every 30 seconds
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_data)
        self.refresh_timer.start(30000)
    
    def init_ui(self):
        """Initialize the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and refresh button
        header_layout = QHBoxLayout()
        title = QLabel("📊 Productivity Metrics")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setFixedWidth(100)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        # Overview Cards
        cards_layout = self.create_overview_cards()
        layout.addLayout(cards_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_leaderboard_tab(), "🏆 Leaderboard")
        self.tabs.addTab(self.create_individual_tab(), "📊 Individual Stats")
        layout.addWidget(self.tabs)
    
    def create_overview_cards(self):
        """Create overview metric cards"""
        cards_layout = QHBoxLayout()
        
        # Today's N-Points
        self.today_card = self.create_metric_card("Today's N-Points", "0", "#4CAF50")
        cards_layout.addWidget(self.today_card)
        
        # This Week's N-Points
        self.week_card = self.create_metric_card("This Week", "0", "#2196F3")
        cards_layout.addWidget(self.week_card)
        
        # Team Total
        self.team_card = self.create_metric_card("Team Total", "0", "#FF9800")
        cards_layout.addWidget(self.team_card)
        
        # Average per Person
        self.avg_card = self.create_metric_card("Avg/Person", "0", "#9C27B0")
        cards_layout.addWidget(self.avg_card)
        
        return cards_layout
    
    def create_metric_card(self, title, value, color):
        """Create a single metric card"""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 10px;
                padding: 15px;
            }}
            QLabel {{
                color: white;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        title_label.setAlignment(Qt.AlignCenter)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setObjectName("value_label")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card
    
    def update_card_value(self, card, value):
        """Update a card's value"""
        value_label = card.findChild(QLabel, "value_label")
        if value_label:
            value_label.setText(str(value))
    
    def create_leaderboard_tab(self):
        """Create the leaderboard tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Period selector
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Period:"))
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Today", "This Week", "This Month"])
        self.period_combo.setCurrentText("This Week")
        self.period_combo.currentTextChanged.connect(self.load_leaderboard)
        period_layout.addWidget(self.period_combo)
        period_layout.addStretch()
        
        layout.addLayout(period_layout)
        
        # Leaderboard table
        self.leaderboard_table = QTableWidget()
        self.leaderboard_table.setColumnCount(6)
        self.leaderboard_table.setHorizontalHeaderLabels([
            "Rank", "Executor", "Full Name", "Points", "Trend", "Badge"
        ])
        self.leaderboard_table.horizontalHeader().setStretchLastSection(True)
        self.leaderboard_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.leaderboard_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Set column widths
        self.leaderboard_table.setColumnWidth(0, 80)   # Rank
        self.leaderboard_table.setColumnWidth(1, 120)  # Executor
        self.leaderboard_table.setColumnWidth(2, 150)  # Full Name
        self.leaderboard_table.setColumnWidth(3, 100)  # Points
        self.leaderboard_table.setColumnWidth(4, 80)   # Trend
        
        layout.addWidget(self.leaderboard_table)
        
        # Team average label
        self.team_avg_label = QLabel("Team Average: 0 points")
        self.team_avg_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.team_avg_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.team_avg_label)
        
        return widget
    
    def create_individual_tab(self):
        """Create the individual stats tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Executor selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select Executor:"))
        
        self.executor_combo = QComboBox()
        self.executor_combo.currentTextChanged.connect(self.load_individual_stats)
        selector_layout.addWidget(self.executor_combo)
        selector_layout.addStretch()
        
        layout.addLayout(selector_layout)
        
        # Stats cards
        self.individual_cards = self.create_individual_cards()
        layout.addLayout(self.individual_cards)
        
        # Daily breakdown table
        self.daily_table = QTableWidget()
        self.daily_table.setColumnCount(5)
        self.daily_table.setHorizontalHeaderLabels([
            "Date", "N-Points", "Test Cases", "P0", "P1"
        ])
        self.daily_table.horizontalHeader().setStretchLastSection(True)
        self.daily_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(QLabel("Daily Breakdown:"))
        layout.addWidget(self.daily_table)
        
        return widget
    
    def create_individual_cards(self):
        """Create metric cards for individual stats"""
        cards_layout = QHBoxLayout()
        
        self.ind_total_card = self.create_metric_card("Total N-Points", "0", "#4CAF50")
        self.ind_cases_card = self.create_metric_card("Test Cases", "0", "#2196F3")
        self.ind_avg_card = self.create_metric_card("Avg/Test", "0", "#FF9800")
        
        cards_layout.addWidget(self.ind_total_card)
        cards_layout.addWidget(self.ind_cases_card)
        cards_layout.addWidget(self.ind_avg_card)
        
        return cards_layout
    
    def load_data(self):
        """Load all productivity data"""
        self.load_overview_data()
        self.load_leaderboard()
        self.populate_executor_dropdown()
    
    def load_overview_data(self):
        """Load overview metrics"""
        try:
            # Get today's data
            response_today = requests.get(
                f"{self.server_url}/productivity/leaderboard?period=day",
                headers=self.headers,
                timeout=5
            )
            
            # Get week's data
            response_week = requests.get(
                f"{self.server_url}/productivity/leaderboard?period=week",
                headers=self.headers,
                timeout=5
            )
            
            if response_today.status_code == 200:
                data = response_today.json()
                today_total = sum(item["points"] for item in data.get("leaderboard", []))
                self.update_card_value(self.today_card, today_total)
            
            if response_week.status_code == 200:
                data = response_week.json()
                week_total = sum(item["points"] for item in data.get("leaderboard", []))
                team_avg = data.get("team_average", 0)
                
                self.update_card_value(self.week_card, week_total)
                self.update_card_value(self.team_card, week_total)
                self.update_card_value(self.avg_card, team_avg)
        
        except Exception as e:
            print(f"Error loading overview data: {e}")
    
    def load_leaderboard(self):
        """Load leaderboard data"""
        period_map = {
            "Today": "day",
            "This Week": "week",
            "This Month": "month"
        }
        
        period = period_map.get(self.period_combo.currentText(), "week")
        
        try:
            response = requests.get(
                f"{self.server_url}/productivity/leaderboard?period={period}",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.populate_leaderboard(data)
            else:
                print(f"Failed to load leaderboard: {response.status_code}")
        
        except Exception as e:
            print(f"Error loading leaderboard: {e}")
    
    def populate_leaderboard(self, data):
        """Populate the leaderboard table"""
        leaderboard = data.get("leaderboard", [])
        team_average = data.get("team_average", 0)
        
        self.leaderboard_table.setRowCount(len(leaderboard))
        
        for i, entry in enumerate(leaderboard):
            rank = entry.get("rank", i + 1)
            username = entry.get("username", "")
            full_name = entry.get("full_name", "")
            points = entry.get("points", 0)
            
            # Rank with medal emoji
            rank_text = f"{rank}"
            if rank == 1:
                rank_text = "🥇 1"
            elif rank == 2:
                rank_text = "🥈 2"
            elif rank == 3:
                rank_text = "🥉 3"
            
            rank_item = QTableWidgetItem(rank_text)
            rank_item.setTextAlignment(Qt.AlignCenter)
            
            username_item = QTableWidgetItem(username)
            fullname_item = QTableWidgetItem(full_name)
            points_item = QTableWidgetItem(str(points))
            points_item.setTextAlignment(Qt.AlignCenter)
            
            # Trend (placeholder for now - could add week-over-week comparison)
            trend_item = QTableWidgetItem("—")
            trend_item.setTextAlignment(Qt.AlignCenter)
            
            # Badge (based on performance)
            badge = ""
            if points > team_average * 1.2:
                badge = "⭐ Top Performer"
            elif points > team_average:
                badge = "✓ Above Average"
            badge_item = QTableWidgetItem(badge)
            
            self.leaderboard_table.setItem(i, 0, rank_item)
            self.leaderboard_table.setItem(i, 1, username_item)
            self.leaderboard_table.setItem(i, 2, fullname_item)
            self.leaderboard_table.setItem(i, 3, points_item)
            self.leaderboard_table.setItem(i, 4, trend_item)
            self.leaderboard_table.setItem(i, 5, badge_item)
            
            # Color code rows
            if rank <= 3:
                bg_color = QColor("#FFF9C4")  # Light yellow for top 3
                for j in range(6):
                    if self.leaderboard_table.item(i, j):
                        self.leaderboard_table.item(i, j).setBackground(bg_color)
        
        self.team_avg_label.setText(f"Team Average: {team_average} points")
    
    def populate_executor_dropdown(self):
        """Populate the executor dropdown with all executors"""
        try:
            response = requests.get(
                f"{self.server_url}/productivity/leaderboard?period=week",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                leaderboard = data.get("leaderboard", [])
                
                current_text = self.executor_combo.currentText()
                self.executor_combo.clear()
                
                for entry in leaderboard:
                    username = entry.get("username", "")
                    full_name = entry.get("full_name", "")
                    display_text = f"{full_name} ({username})"
                    self.executor_combo.addItem(display_text, username)
                
                # Restore selection if possible
                if current_text:
                    index = self.executor_combo.findText(current_text)
                    if index >= 0:
                        self.executor_combo.setCurrentIndex(index)
        
        except Exception as e:
            print(f"Error populating executor dropdown: {e}")
    
    def load_individual_stats(self):
        """Load individual executor stats"""
        if self.executor_combo.count() == 0:
            return
        
        username = self.executor_combo.currentData()
        if not username:
            return
        
        try:
            # Get weekly stats
            response = requests.get(
                f"{self.server_url}/productivity/weekly/{username}",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                total_points = data.get("total_n_points", 0)
                test_cases = data.get("test_cases_completed", 0)
                avg_per_test = total_points / max(test_cases, 1)
                
                self.update_card_value(self.ind_total_card, total_points)
                self.update_card_value(self.ind_cases_card, test_cases)
                self.update_card_value(self.ind_avg_card, f"{avg_per_test:.1f}")
                
                # Populate daily breakdown
                daily_data = data.get("daily_breakdown", [])
                self.populate_daily_breakdown(daily_data, username)
        
        except Exception as e:
            print(f"Error loading individual stats: {e}")
    
    def populate_daily_breakdown(self, daily_data, username):
        """Populate the daily breakdown table"""
        self.daily_table.setRowCount(len(daily_data))
        
        for i, day in enumerate(daily_data):
            date = day.get("date", "")
            points = day.get("points", 0)
            
            date_item = QTableWidgetItem(date)
            points_item = QTableWidgetItem(str(points))
            points_item.setTextAlignment(Qt.AlignCenter)
            
            # Placeholder for detailed suite breakdown
            cases_item = QTableWidgetItem("—")
            p0_item = QTableWidgetItem("—")
            p1_item = QTableWidgetItem("—")
            
            self.daily_table.setItem(i, 0, date_item)
            self.daily_table.setItem(i, 1, points_item)
            self.daily_table.setItem(i, 2, cases_item)
            self.daily_table.setItem(i, 3, p0_item)
            self.daily_table.setItem(i, 4, p1_item)
