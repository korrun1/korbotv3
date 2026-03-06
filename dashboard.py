"""
🎨 KorBot X Enhanced - Advanced Dashboard
Version: 2.0
Date: 2026-02-16

Advanced PyQt6 GUI with intelligent trading modes and full control.
"""

import sys
import logging
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTextEdit, QGroupBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
    QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox,
    QGridLayout, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon
import pyqtgraph as pg

from config_loader import get_config
from main import KorBotX
from utils import setup_logger

logger = logging.getLogger(__name__)


# ============================================================================
# TRADING MODES
# ============================================================================

class TradingMode:
    """Trading mode configurations"""
    
    SAFE = {
        'name': 'وضع الأمان 🛡️',
        'description': 'مثالي للحسابات الصغيرة - حذر جداً',
        'risk_percent': 0.3,
        'max_positions': 1,
        'min_confidence': 0.80,
        'strategies': {
            'scalping': False,
            'mean_reversion': True,
            'breakout': False,
            'adaptive_swing': True
        },
        'aggressive': False,
        'color': '#4CAF50'  # Green
    }
    
    BALANCED = {
        'name': 'وضع متوازن ⚖️',
        'description': 'توازن بين الأمان والربح',
        'risk_percent': 0.8,
        'max_positions': 2,
        'min_confidence': 0.70,
        'strategies': {
            'scalping': True,
            'mean_reversion': True,
            'breakout': True,
            'adaptive_swing': True
        },
        'aggressive': False,
        'color': '#2196F3'  # Blue
    }
    
    AGGRESSIVE = {
        'name': 'وضع المخاطرة 🚀',
        'description': 'للحسابات الكبيرة - ربح عالي',
        'risk_percent': 1.5,
        'max_positions': 3,
        'min_confidence': 0.65,
        'strategies': {
            'scalping': True,
            'mean_reversion': True,
            'breakout': True,
            'adaptive_swing': True
        },
        'aggressive': True,
        'color': '#FF5722'  # Orange-Red
    }
    
    AUTO = {
        'name': 'وضع تلقائي 🤖',
        'description': 'يختار الأفضل حسب السوق',
        'risk_percent': 0.8,
        'max_positions': 2,
        'min_confidence': 0.70,
        'strategies': {
            'scalping': True,
            'mean_reversion': True,
            'breakout': True,
            'adaptive_swing': True
        },
        'aggressive': False,
        'auto_adjust': True,
        'color': '#9C27B0'  # Purple
    }


# ============================================================================
# BOT THREAD
# ============================================================================

class BotThread(QThread):
    """Thread for running the bot"""
    
    status_update = pyqtSignal(str)
    trade_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, config_path: str):
        super().__init__()
        self.config_path = config_path
        self.bot = None
        self.running = False
    
    def run(self):
        """Run the bot"""
        try:
            self.status_update.emit("🚀 بدء تشغيل البوت...")
            self.bot = KorBotX(self.config_path)
            self.running = True
            
            self.status_update.emit("✅ البوت يعمل الآن!")
            
            # Start bot in thread
            self.bot.start()
            
        except Exception as e:
            self.error_signal.emit(f"خطأ: {str(e)}")
            logger.error(f"Bot thread error: {e}", exc_info=True)
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        if self.bot:
            self.bot.stop("إيقاف من الواجهة")
        self.quit()
        self.wait()


# ============================================================================
# MAIN DASHBOARD
# ============================================================================

class KorBotDashboard(QMainWindow):
    """Advanced KorBot X Dashboard"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("🤖 KorBot X Enhanced - لوحة التحكم المتقدمة")
        self.setGeometry(100, 100, 1400, 900)
        
        # State
        self.bot_thread = None
        self.is_running = False
        self.current_mode = 'BALANCED'
        self.config = get_config()
        
        # Setup UI
        self._setup_ui()
        self._apply_dark_theme()
        
        # Setup timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_dashboard)
        self.update_timer.start(1000)  # Update every second
        
        logger.info("Dashboard initialized")
    
    def _setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Main content (splitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Controls
        left_panel = self._create_control_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Display
        right_panel = self._create_display_panel()
        splitter.addWidget(right_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("⏸️ البوت متوقف")
    
    def _create_header(self) -> QWidget:
        """Create header section"""
        header = QFrame()
        header.setFrameShape(QFrame.Shape.StyledPanel)
        header.setStyleSheet("background-color: #1e1e1e; border-radius: 5px;")
        
        layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("🤖 KorBot X Enhanced")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #4CAF50;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("⚫")
        self.status_indicator.setFont(QFont("Arial", 20))
        layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("متوقف")
        self.status_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.status_label)
        
        return header
    
    def _create_control_panel(self) -> QWidget:
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Start/Stop buttons
        control_group = self._create_control_buttons()
        layout.addWidget(control_group)
        
        # Trading mode selector
        mode_group = self._create_mode_selector()
        layout.addWidget(mode_group)
        
        # Account info
        account_group = self._create_account_info()
        layout.addWidget(account_group)
        
        # Risk settings
        risk_group = self._create_risk_settings()
        layout.addWidget(risk_group)
        
        # Strategy toggles
        strategy_group = self._create_strategy_toggles()
        layout.addWidget(strategy_group)
        
        layout.addStretch()
        
        return panel
    
    def _create_control_buttons(self) -> QGroupBox:
        """Create start/stop control buttons"""
        group = QGroupBox("🎮 التحكم")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QVBoxLayout()
        
        # Start button
        self.start_btn = QPushButton("▶️ تشغيل البوت")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_btn.clicked.connect(self._start_bot)
        layout.addWidget(self.start_btn)
        
        # Stop button
        self.stop_btn = QPushButton("⏹️ إيقاف البوت")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.clicked.connect(self._stop_bot)
        layout.addWidget(self.stop_btn)
        
        # Pause button
        self.pause_btn = QPushButton("⏸️ إيقاف مؤقت")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.pause_btn.clicked.connect(self._pause_bot)
        layout.addWidget(self.pause_btn)
        
        group.setLayout(layout)
        return group
    
    def _create_mode_selector(self) -> QGroupBox:
        """Create trading mode selector"""
        group = QGroupBox("🎯 وضع التداول")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QVBoxLayout()
        
        # Mode combo
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "🛡️ وضع الأمان (للحسابات الصغيرة)",
            "⚖️ وضع متوازن (موصى به)",
            "🚀 وضع المخاطرة (ربح عالي)",
            "🤖 وضع تلقائي (ذكي)"
        ])
        self.mode_combo.setCurrentIndex(1)  # Balanced default
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.mode_combo.setStyleSheet("font-size: 13px; padding: 8px;")
        layout.addWidget(self.mode_combo)
        
        # Mode description
        self.mode_description = QLabel()
        self.mode_description.setWordWrap(True)
        self.mode_description.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                padding: 10px;
                border-radius: 5px;
                color: #aaaaaa;
            }
        """)
        layout.addWidget(self.mode_description)
        
        # Update description
        self._update_mode_description()
        
        group.setLayout(layout)
        return group
    
    def _create_account_info(self) -> QGroupBox:
        """Create account information display"""
        group = QGroupBox("💰 معلومات الحساب")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QGridLayout()
        
        # Balance
        layout.addWidget(QLabel("الرصيد:"), 0, 0)
        self.balance_label = QLabel("$0.00")
        self.balance_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
        layout.addWidget(self.balance_label, 0, 1)
        
        # Equity
        layout.addWidget(QLabel("القيمة:"), 1, 0)
        self.equity_label = QLabel("$0.00")
        self.equity_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.equity_label, 1, 1)
        
        # Profit
        layout.addWidget(QLabel("الربح:"), 2, 0)
        self.profit_label = QLabel("$0.00")
        self.profit_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.profit_label, 2, 1)
        
        # Open trades
        layout.addWidget(QLabel("الصفقات المفتوحة:"), 3, 0)
        self.trades_label = QLabel("0")
        self.trades_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2196F3;")
        layout.addWidget(self.trades_label, 3, 1)
        
        group.setLayout(layout)
        return group
    
    def _create_risk_settings(self) -> QGroupBox:
        """Create risk management settings"""
        group = QGroupBox("⚠️ إعدادات المخاطرة")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QGridLayout()
        
        # Risk percentage
        layout.addWidget(QLabel("نسبة المخاطرة:"), 0, 0)
        self.risk_spin = QDoubleSpinBox()
        self.risk_spin.setRange(0.1, 5.0)
        self.risk_spin.setValue(0.8)
        self.risk_spin.setSingleStep(0.1)
        self.risk_spin.setSuffix("%")
        self.risk_spin.valueChanged.connect(self._on_risk_changed)
        layout.addWidget(self.risk_spin, 0, 1)
        
        # Max positions
        layout.addWidget(QLabel("الحد الأقصى للصفقات:"), 1, 0)
        self.positions_spin = QSpinBox()
        self.positions_spin.setRange(1, 5)
        self.positions_spin.setValue(2)
        self.positions_spin.valueChanged.connect(self._on_positions_changed)
        layout.addWidget(self.positions_spin, 1, 1)
        
        # Min confidence
        layout.addWidget(QLabel("الحد الأدنى للثقة:"), 2, 0)
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(50, 95)
        self.confidence_slider.setValue(70)
        self.confidence_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.confidence_slider.setTickInterval(5)
        self.confidence_slider.valueChanged.connect(self._on_confidence_changed)
        layout.addWidget(self.confidence_slider, 2, 1)
        
        self.confidence_label = QLabel("70%")
        self.confidence_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.confidence_label, 2, 2)
        
        group.setLayout(layout)
        return group
    
    def _create_strategy_toggles(self) -> QGroupBox:
        """Create strategy enable/disable toggles"""
        group = QGroupBox("📊 الاستراتيجيات")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QVBoxLayout()
        
        # Scalping
        self.scalping_check = QCheckBox("⚡ Scalping (M1)")
        self.scalping_check.setChecked(True)
        self.scalping_check.stateChanged.connect(self._on_strategy_changed)
        layout.addWidget(self.scalping_check)
        
        # Mean Reversion
        self.mean_reversion_check = QCheckBox("🔄 Mean Reversion (M5)")
        self.mean_reversion_check.setChecked(True)
        self.mean_reversion_check.stateChanged.connect(self._on_strategy_changed)
        layout.addWidget(self.mean_reversion_check)
        
        # Breakout
        self.breakout_check = QCheckBox("💥 Breakout (H1)")
        self.breakout_check.setChecked(True)
        self.breakout_check.stateChanged.connect(self._on_strategy_changed)
        layout.addWidget(self.breakout_check)
        
        # Swing
        self.swing_check = QCheckBox("🌊 Adaptive Swing (H4)")
        self.swing_check.setChecked(True)
        self.swing_check.stateChanged.connect(self._on_strategy_changed)
        layout.addWidget(self.swing_check)
        
        group.setLayout(layout)
        return group
    
    def _create_display_panel(self) -> QWidget:
        """Create right display panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tabs
        tabs = QTabWidget()
        tabs.setFont(QFont("Arial", 11))
        
        # Performance tab
        performance_tab = self._create_performance_tab()
        tabs.addTab(performance_tab, "📈 الأداء")
        
        # Trades tab
        trades_tab = self._create_trades_tab()
        tabs.addTab(trades_tab, "💼 الصفقات")
        
        # Logs tab
        logs_tab = self._create_logs_tab()
        tabs.addTab(logs_tab, "📝 السجلات")
        
        # Statistics tab
        stats_tab = self._create_statistics_tab()
        tabs.addTab(stats_tab, "📊 الإحصائيات")
        
        layout.addWidget(tabs)
        
        return panel
    
    def _create_performance_tab(self) -> QWidget:
        """Create performance metrics tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Metrics grid
        metrics_group = QGroupBox("📊 مقاييس الأداء")
        metrics_layout = QGridLayout()
        
        # Win rate
        metrics_layout.addWidget(QLabel("نسبة النجاح:"), 0, 0)
        self.win_rate_label = QLabel("0.0%")
        self.win_rate_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        metrics_layout.addWidget(self.win_rate_label, 0, 1)
        
        self.win_rate_bar = QProgressBar()
        self.win_rate_bar.setRange(0, 100)
        self.win_rate_bar.setValue(0)
        metrics_layout.addWidget(self.win_rate_bar, 0, 2)
        
        # Profit factor
        metrics_layout.addWidget(QLabel("عامل الربح:"), 1, 0)
        self.profit_factor_label = QLabel("0.00")
        self.profit_factor_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        metrics_layout.addWidget(self.profit_factor_label, 1, 1)
        
        # Sharpe ratio
        metrics_layout.addWidget(QLabel("Sharpe Ratio:"), 2, 0)
        self.sharpe_label = QLabel("0.00")
        self.sharpe_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        metrics_layout.addWidget(self.sharpe_label, 2, 1)
        
        # Drawdown
        metrics_layout.addWidget(QLabel("الانخفاض:"), 3, 0)
        self.drawdown_label = QLabel("0.0%")
        self.drawdown_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f44336;")
        metrics_layout.addWidget(self.drawdown_label, 3, 1)
        
        self.drawdown_bar = QProgressBar()
        self.drawdown_bar.setRange(0, 100)
        self.drawdown_bar.setValue(0)
        self.drawdown_bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
        metrics_layout.addWidget(self.drawdown_bar, 3, 2)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Equity curve
        curve_group = QGroupBox("📈 منحنى القيمة")
        curve_layout = QVBoxLayout()
        
        self.equity_plot = pg.PlotWidget()
        self.equity_plot.setBackground('#1e1e1e')
        self.equity_plot.setLabel('left', 'Equity', units='$')
        self.equity_plot.setLabel('bottom', 'Time')
        self.equity_plot.showGrid(x=True, y=True, alpha=0.3)
        
        curve_layout.addWidget(self.equity_plot)
        curve_group.setLayout(curve_layout)
        layout.addWidget(curve_group)
        
        return widget
    
    def _create_trades_tab(self) -> QWidget:
        """Create trades display tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Trades table
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(8)
        self.trades_table.setHorizontalHeaderLabels([
            "الوقت", "الرمز", "النوع", "الاستراتيجية",
            "السعر", "الربح/الخسارة", "الحالة", "الثقة"
        ])
        self.trades_table.horizontalHeader().setStretchLastSection(True)
        self.trades_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.trades_table)
        
        return widget
    
    def _create_logs_tab(self) -> QWidget:
        """Create logs display tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logs text area
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Courier New", 10))
        self.logs_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #444;
            }
        """)
        
        layout.addWidget(self.logs_text)
        
        # Clear button
        clear_btn = QPushButton("🗑️ مسح السجلات")
        clear_btn.clicked.connect(lambda: self.logs_text.clear())
        layout.addWidget(clear_btn)
        
        return widget
    
    def _create_statistics_tab(self) -> QWidget:
        """Create statistics tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Stats grid
        stats_group = QGroupBox("📈 إحصائيات مفصلة")
        stats_layout = QGridLayout()
        
        stats_items = [
            ("إجمالي الصفقات:", "total_trades"),
            ("الصفقات الرابحة:", "winning_trades"),
            ("الصفقات الخاسرة:", "losing_trades"),
            ("متوسط الربح:", "avg_win"),
            ("متوسط الخسارة:", "avg_loss"),
            ("أكبر ربح:", "largest_win"),
            ("أكبر خسارة:", "largest_loss"),
            ("الربح الإجمالي:", "total_profit"),
        ]
        
        self.stats_labels = {}
        
        for i, (label, key) in enumerate(stats_items):
            stats_layout.addWidget(QLabel(label), i, 0)
            value_label = QLabel("0")
            value_label.setStyleSheet("font-weight: bold; font-size: 13px;")
            stats_layout.addWidget(value_label, i, 1)
            self.stats_labels[key] = value_label
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        
        return widget
    
    def _apply_dark_theme(self):
        """Apply dark theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                border: 2px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                color: white;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
                border: 1px solid #888;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2d2d2d;
                gridline-color: #444;
                border: 1px solid #555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: white;
                padding: 5px;
                border: 1px solid #555;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    
    def _start_bot(self):
        """Start the trading bot"""
        try:
            # Apply current settings
            self._apply_current_settings()
            
            # Start bot thread
            self.bot_thread = BotThread("config/config.yaml")
            self.bot_thread.status_update.connect(self._on_bot_status)
            self.bot_thread.error_signal.connect(self._on_bot_error)
            self.bot_thread.start()
            
            # Update UI
            self.is_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
            
            self.status_indicator.setText("🟢")
            self.status_label.setText("يعمل")
            self.statusBar().showMessage("▶️ البوت يعمل...")
            
            self._log("✅ تم بدء تشغيل البوت بنجاح")
            
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل بدء البوت:\n{str(e)}")
            logger.error(f"Error starting bot: {e}", exc_info=True)
    
    def _stop_bot(self):
        """Stop the trading bot"""
        if self.bot_thread:
            self.bot_thread.stop()
        
        # Update UI
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        
        self.status_indicator.setText("⚫")
        self.status_label.setText("متوقف")
        self.statusBar().showMessage("⏹️ البوت متوقف")
        
        self._log("🛑 تم إيقاف البوت")
    
    def _pause_bot(self):
        """Pause the trading bot"""
        # Toggle pause state
        if self.bot_thread and self.bot_thread.bot:
            self.bot_thread.bot.paused = not self.bot_thread.bot.paused
            
            if self.bot_thread.bot.paused:
                self.status_indicator.setText("🟡")
                self.status_label.setText("متوقف مؤقتاً")
                self.pause_btn.setText("▶️ استئناف")
                self._log("⏸️ تم الإيقاف المؤقت")
            else:
                self.status_indicator.setText("🟢")
                self.status_label.setText("يعمل")
                self.pause_btn.setText("⏸️ إيقاف مؤقت")
                self._log("▶️ تم الاستئناف")
    
    def _on_mode_changed(self, index):
        """Handle trading mode change"""
        modes = ['SAFE', 'BALANCED', 'AGGRESSIVE', 'AUTO']
        self.current_mode = modes[index]
        
        mode_config = getattr(TradingMode, self.current_mode)
        
        # Update settings based on mode
        self.risk_spin.setValue(mode_config['risk_percent'])
        self.positions_spin.setValue(mode_config['max_positions'])
        self.confidence_slider.setValue(int(mode_config['min_confidence'] * 100))
        
        # Update strategies
        strategies = mode_config['strategies']
        self.scalping_check.setChecked(strategies['scalping'])
        self.mean_reversion_check.setChecked(strategies['mean_reversion'])
        self.breakout_check.setChecked(strategies['breakout'])
        self.swing_check.setChecked(strategies['adaptive_swing'])
        
        # Update description
        self._update_mode_description()
        
        self._log(f"🎯 تم تغيير الوضع إلى: {mode_config['name']}")
    
    def _update_mode_description(self):
        """Update mode description label"""
        mode_config = getattr(TradingMode, self.current_mode)
        self.mode_description.setText(mode_config['description'])
        self.mode_description.setStyleSheet(f"""
            QLabel {{
                background-color: {mode_config['color']};
                padding: 10px;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }}
        """)
    
    def _on_risk_changed(self, value):
        """Handle risk percentage change"""
        self._log(f"⚠️ تم تغيير نسبة المخاطرة إلى: {value}%")
    
    def _on_positions_changed(self, value):
        """Handle max positions change"""
        self._log(f"📊 تم تغيير الحد الأقصى للصفقات إلى: {value}")
    
    def _on_confidence_changed(self, value):
        """Handle confidence threshold change"""
        self.confidence_label.setText(f"{value}%")
        self._log(f"🎯 تم تغيير الحد الأدنى للثقة إلى: {value}%")
    
    def _on_strategy_changed(self):
        """Handle strategy toggle"""
        strategies = {
            'Scalping': self.scalping_check.isChecked(),
            'Mean Reversion': self.mean_reversion_check.isChecked(),
            'Breakout': self.breakout_check.isChecked(),
            'Swing': self.swing_check.isChecked()
        }
        
        enabled = [k for k, v in strategies.items() if v]
        self._log(f"📊 الاستراتيجيات المفعلة: {', '.join(enabled)}")
    
    def _apply_current_settings(self):
        """Apply current settings to config"""
        # Update config with current UI settings
        self.config.config['risk']['base_risk_percent'] = self.risk_spin.value()
        self.config.config['risk']['max_positions'] = self.positions_spin.value()
        self.config.config['ai']['xgboost']['min_confidence'] = self.confidence_slider.value() / 100
        
        # Update strategies
        self.config.config['trading']['strategies'] = {
            'scalping': self.scalping_check.isChecked(),
            'mean_reversion': self.mean_reversion_check.isChecked(),
            'breakout': self.breakout_check.isChecked(),
            'adaptive_swing': self.swing_check.isChecked()
        }
    
    def _on_bot_status(self, message: str):
        """Handle bot status update"""
        self._log(message)
    
    def _on_bot_error(self, error: str):
        """Handle bot error"""
        self._log(f"❌ خطأ: {error}")
        QMessageBox.critical(self, "خطأ", error)
    
    def _update_dashboard(self):
        """Update dashboard with latest data"""
        if not self.is_running or not self.bot_thread or not self.bot_thread.bot:
            return
        
        try:
            bot = self.bot_thread.bot
            
            # Update account info
            account_summary = bot.execution_engine.get_account_summary()
            if account_summary:
                self.balance_label.setText(f"${account_summary.get('balance', 0):.2f}")
                self.equity_label.setText(f"${account_summary.get('equity', 0):.2f}")
                
                profit = account_summary.get('profit', 0)
                self.profit_label.setText(f"${profit:.2f}")
                
                if profit > 0:
                    self.profit_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
                elif profit < 0:
                    self.profit_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #f44336;")
                
                self.trades_label.setText(str(account_summary.get('open_trades', 0)))
            
            # Update performance metrics
            risk_metrics = bot.risk_engine.get_metrics_summary()
            if risk_metrics:
                win_rate = risk_metrics.get('win_rate', 0)
                self.win_rate_label.setText(f"{win_rate:.1f}%")
                self.win_rate_bar.setValue(int(win_rate))
                
                drawdown = risk_metrics.get('current_drawdown', 0)
                self.drawdown_label.setText(f"{drawdown:.1f}%")
                self.drawdown_bar.setValue(int(drawdown))
        
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
    
    def _log(self, message: str):
        """Add message to logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        self.logs_text.verticalScrollBar().setValue(
            self.logs_text.verticalScrollBar().maximum()
        )
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.is_running:
            reply = QMessageBox.question(
                self,
                "تأكيد الإغلاق",
                "البوت لا يزال يعمل. هل تريد إيقافه والخروج؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._stop_bot()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("KorBot X Enhanced")
    app.setOrganizationName("KorBot")
    
    # Create and show dashboard
    dashboard = KorBotDashboard()
    dashboard.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
