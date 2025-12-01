import sys
import json
import os
import ctypes
from ctypes import windll, byref, c_int
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTabWidget, QFormLayout, QMessageBox, QScrollArea)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

CONFIG_FILE = "chatcollect_config.json"

DEFAULT_CONFIG = {
    "commands": {
        "loot": "!loot",
        "leaderboard": "!leaderboard",
        "contest": "!contest",
        "use": "!use"
    },
    "messages": {
        "cooldown": "⏳ @{username}, resting...... wait {remaining}s.",
        "loot_success": "🍞 @{username} looted a {item}! (+{points} pts) ({rank}) | Score: {score}",
        "loot_legendary": "✨ @{username} looted a LEGENDARY {item}! ✨ (+{points} pts) ({rank}) | Score: {score}",
        "rank_up": "🎉 {username} ranked up to {rank}!",
        "contest_start": "⚔️ CONTEST STARTED! Type {command} to enter! (Entry: 50 pts)",
        "contest_winner": "🏆 {username} WON THE CONTEST! Prize: {prize} pts!",
        "rush_hour_start": "🚀 RUSH HOUR STARTED! 2x Points for 60 seconds!",
        "loot_drive_start": "🎒 LOOT DRIVE STARTED! Community Goal: {target} Items!",
        "bounty_hunter_spawn": "🧐 BOUNTY HUNTER ARRIVED! He wants a {item}!",
        "bounty_hunter_satisfied": "🧐 {username} satisfied the Bounty Hunter! (+{points} pts)"
    },
    "events": {
        "rush_hour_name": "Rush Hour",
        "loot_drive_name": "Loot Drive",
        "bounty_hunter_name": "Bounty Hunter",
        "contest_name": "Contest"
    },
    "ranks": [
        {"score": 0, "title": "Novice Collector"},
        {"score": 50, "title": "Rookie Scavenger"},
        {"score": 250, "title": "Apprentice Hunter"},
        {"score": 750, "title": "Loot Specialist"},
        {"score": 2000, "title": "Treasure Expert"},
        {"score": 5000, "title": "Hoard Master"},
        {"score": 10000, "title": "Legendary Collector"},
        {"score": 25000, "title": "Artifact Hunter"},
        {"score": 50000, "title": "Celestial Hoarder"},
        {"score": 100000, "title": "God of Loot"}
    ]
}

class ConfigEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatCollect Setup")
        self.setGeometry(100, 100, 800, 600)
        
        if os.path.exists("exe_icon.ico"):
            self.setWindowIcon(QIcon("exe_icon.ico"))

        # Enable Dark Title Bar (Windows 10/11)
        try:
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            hwnd = int(self.winId())
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), 4)
        except Exception:
            pass

        # Dark mode stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-size: 11pt;
            }
            QGroupBox {
                background-color: #252525;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 5px;
                color: #e0e0e0;
                selection-background-color: #4a4a4a;
            }
            QLineEdit:focus {
                border: 1px solid #0d7377;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 8px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QTextEdit {
                background-color: #0d0d0d;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                color: #e0e0e0;
                selection-background-color: #4a4a4a;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 10px 20px;
                border: 1px solid #3d3d3d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
                font-weight: bold;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.config = self.load_config()
        self.inputs = {}
        self.rank_inputs = []

        self.init_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Ensure ranks exist
                    if "ranks" not in loaded:
                        loaded["ranks"] = DEFAULT_CONFIG["ranks"]
                    return loaded
            except:
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel("ChatCollect Configuration")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # --- Commands Tab ---
        cmd_tab = QWidget()
        cmd_layout = QFormLayout()
        
        self.add_input(cmd_layout, "commands", "loot", "Loot Command:")
        self.add_input(cmd_layout, "commands", "leaderboard", "Leaderboard Command:")
        self.add_input(cmd_layout, "commands", "contest", "Contest Command:")
        self.add_input(cmd_layout, "commands", "use", "Use Item Command:")
        
        cmd_tab.setLayout(cmd_layout)
        tabs.addTab(cmd_tab, "💬 Commands")

        # --- Messages Tab ---
        msg_tab = QWidget()
        msg_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QFormLayout(scroll_content)
        
        self.add_input(scroll_layout, "messages", "cooldown", "Cooldown Message:")
        self.add_input(scroll_layout, "messages", "loot_success", "Loot Success:")
        self.add_input(scroll_layout, "messages", "loot_legendary", "Legendary Loot:")
        self.add_input(scroll_layout, "messages", "rank_up", "Rank Up:")
        self.add_input(scroll_layout, "messages", "contest_start", "Contest Start:")
        self.add_input(scroll_layout, "messages", "contest_winner", "Contest Winner:")
        self.add_input(scroll_layout, "messages", "rush_hour_start", "Rush Hour Start:")
        self.add_input(scroll_layout, "messages", "loot_drive_start", "Loot Drive Start:")
        self.add_input(scroll_layout, "messages", "bounty_hunter_spawn", "Bounty Hunter Spawn:")
        self.add_input(scroll_layout, "messages", "bounty_hunter_satisfied", "Bounty Hunter Satisfied:")
        
        scroll.setWidget(scroll_content)
        msg_layout.addWidget(scroll)
        msg_tab.setLayout(msg_layout)
        tabs.addTab(msg_tab, "📢 Messages")

        # --- Events Tab ---
        evt_tab = QWidget()
        evt_layout = QFormLayout()
        
        self.add_input(evt_layout, "events", "rush_hour_name", "Rush Hour Name:")
        self.add_input(evt_layout, "events", "loot_drive_name", "Loot Drive Name:")
        self.add_input(evt_layout, "events", "bounty_hunter_name", "Bounty Hunter Name:")
        self.add_input(evt_layout, "events", "contest_name", "Contest Name:")
        
        evt_tab.setLayout(evt_layout)
        tabs.addTab(evt_tab, "🎉 Events")

        # --- Ranks Tab ---
        ranks_tab = QWidget()
        ranks_layout = QVBoxLayout()
        
        # Scroll Area for Ranks
        rank_scroll = QScrollArea()
        rank_scroll.setWidgetResizable(True)
        rank_scroll_content = QWidget()
        self.ranks_layout = QVBoxLayout(rank_scroll_content)
        
        # Load ranks
        current_ranks = self.config.get("ranks", DEFAULT_CONFIG["ranks"])
        # Sort by score
        current_ranks.sort(key=lambda x: x["score"])
        
        for r in current_ranks:
            self.add_rank_row(r["score"], r["title"])
            
        # Add spacer to push items up
        self.ranks_layout.addStretch()
            
        rank_scroll.setWidget(rank_scroll_content)
        ranks_layout.addWidget(rank_scroll)
        
        # Add Rank Button
        add_rank_btn = QPushButton("➕ Add New Rank")
        add_rank_btn.clicked.connect(lambda: self.add_rank_row(0, "New Rank"))
        ranks_layout.addWidget(add_rank_btn)
        
        ranks_tab.setLayout(ranks_layout)
        tabs.addTab(ranks_tab, "🏆 Ranks")

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        save_btn.clicked.connect(self.save_config)
        
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px;")
        reset_btn.clicked.connect(self.reset_defaults)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(reset_btn)
        
        main_layout.addLayout(btn_layout)
        
        # Footer
        header = QLabel("Note: Restart ChatCollect.exe after saving changes.")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-top: 10px;")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

    def add_input(self, layout, category, key, label_text):
        label = QLabel(label_text)
        default_val = DEFAULT_CONFIG[category].get(key, "")
        current_val = self.config.get(category, {}).get(key, default_val)
        
        inp = QLineEdit(str(current_val))
        layout.addRow(label, inp)
        self.inputs[f"{category}.{key}"] = inp

    def add_rank_row(self, score, title):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 5, 0, 5)
        
        score_input = QLineEdit(str(score))
        score_input.setPlaceholderText("Score")
        score_input.setFixedWidth(100)
        score_input.setValidator(None) # Could add IntValidator
        
        title_input = QLineEdit(title)
        title_input.setPlaceholderText("Rank Title")
        
        del_btn = QPushButton("❌")
        del_btn.setFixedWidth(40)
        del_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        del_btn.clicked.connect(lambda: self.remove_rank_row(row_widget, score_input, title_input))
        
        row_layout.addWidget(QLabel("Score:"))
        row_layout.addWidget(score_input)
        row_layout.addWidget(QLabel("Title:"))
        row_layout.addWidget(title_input)
        row_layout.addWidget(del_btn)
        
        # Insert before the stretch item (last item)
        count = self.ranks_layout.count()
        if count > 0:
            self.ranks_layout.insertWidget(count - 1, row_widget)
        else:
            self.ranks_layout.addWidget(row_widget)
            
        self.rank_inputs.append((row_widget, score_input, title_input))

    def remove_rank_row(self, widget, score_input, title_input):
        self.ranks_layout.removeWidget(widget)
        widget.deleteLater()
        if (widget, score_input, title_input) in self.rank_inputs:
            self.rank_inputs.remove((widget, score_input, title_input))

    def save_config(self):
        new_config = self.config.copy()
        
        # Save Inputs
        for key, inp in self.inputs.items():
            category, field = key.split('.')
            if category not in new_config:
                new_config[category] = {}
            new_config[category][field] = inp.text()
            
        # Save Ranks
        new_ranks = []
        for _, score_inp, title_inp in self.rank_inputs:
            try:
                s = int(score_inp.text())
                t = title_inp.text().strip()
                if t:
                    new_ranks.append({"score": s, "title": t})
            except ValueError:
                pass # Ignore invalid scores
        
        new_ranks.sort(key=lambda x: x["score"])
        new_config["ranks"] = new_ranks
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4)
            QMessageBox.information(self, "Success", "Configuration saved!\nRestart ChatCollect.exe to apply changes.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save config: {e}")

    def reset_defaults(self):
        reply = QMessageBox.question(self, 'Reset Defaults', 
                                     "Are you sure you want to reset all settings to default?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config = DEFAULT_CONFIG.copy()
            # Reload UI
            self.close()
            self.__init__()
            self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = ConfigEditor()
    editor.show()
    sys.exit(app.exec_())
