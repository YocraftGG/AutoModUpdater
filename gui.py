from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from main import *


class DownloadWorker(QThread):
    # כאן אנחנו מגדירים שהסיגנל מקבל str (עבור ה-filename) ו-dict (עבור ה-mod)
    finished = pyqtSignal(str, dict)

    def __init__(self, mod, folder):
        super().__init__()
        self.mod = mod
        self.folder = folder

    def run(self):
        filename = download_mod(self.mod["file_name"], self.folder, self.mod["latest_version"])
        # עכשיו זה יעבוד כי הסיגנל מצפה לשני פרמטרים
        self.finished.emit(filename, self.mod)

# מחלקה חדשה לכרטיס מוד בודד
class ModCard(QFrame):
    def __init__(self, mod, mod_folder, on_update_callback):
        super().__init__()
        self.current_mod_data = None
        self.mod_folder = mod_folder
        self.on_update_callback = on_update_callback  # פונקציה שתיקרא כשלוחצים עדכן

        self.setObjectName("modCard")
        self.set_style()

        # בניית ה-Layout של הכרטיס
        self.layout = QHBoxLayout(self)
        self.info_layout = QVBoxLayout()

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 17px; font-weight: bold; background: transparent;")

        self.version_label = QLabel()
        self.version_label.setStyleSheet("font-size: 12px; color: #aaa; background: transparent;")

        self.update_label = QLabel()
        self.update_label.setStyleSheet("color: #FFD700; font-weight: bold; background: transparent;")

        self.info_layout.addWidget(self.title_label)
        self.info_layout.addWidget(self.version_label)
        self.info_layout.addWidget(self.update_label)

        self.update_btn = QPushButton("Update")
        self.update_btn.setFixedSize(100, 32)
        self.update_btn.setStyleSheet("background-color: #0078D4; color: white; border-radius: 6px; font-weight: bold;")
        self.update_btn.clicked.connect(self.start_update)

        self.status_ok = QLabel("✅ Up to date")
        self.status_ok.setStyleSheet("color: #4CAF50; font-weight: bold; background: transparent;")

        self.layout.addLayout(self.info_layout)
        self.layout.addStretch()
        self.layout.addWidget(self.update_btn)
        self.layout.addWidget(self.status_ok)

        # יצירת פס טעינה (חדש!)
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)  # הופך אותו לאנימציה רצה (Indeterminate)
        self.loading_bar.setFixedHeight(4)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setStyleSheet("""
                    QProgressBar { background: #333; border: none; border-radius: 2px; }
                    QProgressBar::chunk { background: #0078D4; }
                """)
        self.loading_bar.hide()  # מוסתר בהתחלה

        # הוספת פס הטעינה ללייאאוט האנכי של הטקסט (מתחת לגרסה)
        self.info_layout.addWidget(self.loading_bar)

        self.update_data(mod)

    def set_style(self):
        self.setStyleSheet("""
            QFrame#modCard { background-color: #1e1e1e; border-radius: 12px; border: 1px solid #333; }
            QFrame#modCard:hover { background-color: #252525; }
        """)

    def show_loading(self, is_loading):
        """מציג או מחביא את האנימציה ומחליף את הכפתור"""
        if is_loading:
            self.update_btn.hide()
            self.loading_bar.show()
            self.update_label.setText("📥 Downloading...")
        else:
            self.loading_bar.hide()

    def update_data(self, mod):
        """מעדכן רק את הטקסטים והכפתורים של הכרטיס הספציפי הזה"""
        print("refreshing")
        self.current_mod_data = mod
        self.title_label.setText(mod["title"])
        self.version_label.setText(f"Current: {mod['version']}")

        if mod.get("has_update"):
            self.update_label.setText(f"⭐ New: {mod['latest_version']['version_number']}")
            self.update_label.show()
            self.update_btn.show()
            self.status_ok.hide()
        else:
            self.update_label.hide()
            self.update_btn.hide()
            self.status_ok.show()

    def start_update(self):
        # מפעיל את פונקציית ההורדה ומעדכן את הממשק דרך ה-MainWindow
        self.on_update_callback(self.current_mod_data)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mod_folder = "C:/Users/user/AppData/Roaming/.minecraft/mods"
        self.mods = get_mods(self.mod_folder)
        self.mod_widgets = {}  # מילון לשמירת הכרטיסים: {file_name: ModCard_Object}

        self.setWindowTitle("AutoModUpdater")
        self.setGeometry(100, 100, 700, 800)
        self.setStyleSheet("background-color: #121212; color: white; font-family: 'Segoe UI', Arial;")

        self.setWindowIcon(QIcon("AutoModUpdater-Icon.png"))

        # ווידג'ט מרכזי
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # 1. לוגו
        self.logo = QLabel()
        pixmap = QPixmap("AutoModUpdater-Logo-2.png")
        if not pixmap.isNull():
            self.logo.setPixmap(pixmap.scaled(300, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.logo)

        # 2. כפתור "Update All" (נשמור אותו כמשתנה מחלקה כדי שנוכל לעדכן אותו)
        self.update_all_btn = QPushButton()
        self.update_all_btn.setCursor(Qt.PointingHandCursor)
        self.update_all_btn.setFixedHeight(45)
        self.update_all_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2ecc71; color: #000; font-weight: bold; 
                        font-size: 15px; border-radius: 10px; margin: 10px 0px;
                    }
                    QPushButton:hover { background-color: #27ae60; }
                """)
        self.update_all_btn.clicked.connect(self.update_all_mods)
        self.main_layout.addWidget(self.update_all_btn)

        # 3. אזור הגלילה
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.container = QWidget()
        self.mods_layout = QVBoxLayout(self.container)
        self.mods_layout.setAlignment(Qt.AlignTop)
        self.mods_layout.setSpacing(12)

        self.scroll.setWidget(self.container)
        self.main_layout.addWidget(self.scroll)

        self.load_initial_mods()

    def load_initial_mods(self):
        """טעינה ראשונית בלבד"""
        for mod in self.mods:
            card = ModCard(mod, self.mod_folder, self.update_mod)
            self.mods_layout.addWidget(card)
            self.mod_widgets[mod["file_name"]] = card  # שמירה במילון לפי שם קובץ

        self.update_global_button(self.mods)

    def update_mod(self, mod):
        card = self.mod_widgets[mod["file_name"]]
        card.show_loading(True)

        # יצירת רשימה ב-init אם היא לא קיימת: self.workers = []
        worker = DownloadWorker(mod, self.mod_folder)
        worker.finished.connect(self.update_finished)

        # שמירה על ה-worker בחיים
        if not hasattr(self, 'threads'): self.threads = []
        self.threads.append(worker)

        worker.start()

    def update_all_mods(self):
        for mod in get_mods(self.mod_folder):
            if mod["has_update"]:
                self.update_mod(mod)

    def update_finished(self, filename, mod):
        """מה קורה כשמוד מסיים לרדת"""
        updated_mod_data = get_mod(filename, self.mod_folder)

        # עדכון של הכרטיס הספציפי בלבד!
        self.mod_widgets[mod["file_name"]].update_data(updated_mod_data)

        # עדכון המוד ברשימה המרכזית (לפי שם הקובץ המקורי)
        for i, m in enumerate(self.mods):
            if m["file_name"] == mod["file_name"]:
                self.mods[i] = updated_mod_data
                break

        # עדכון הכרטיס והפסקת האנימציה
        card = self.mod_widgets[mod["file_name"]]
        card.show_loading(False)
        card.update_data(updated_mod_data)

        # עדכון כפתור ה-"Update All" הכללי
        self.update_global_button(self.mods)

    def update_global_button(self, mods):
        """מעדכן רק את הטקסט של כפתור ה-'עדכן הכל'"""
        to_update = [m for m in mods if m.get("has_update")]
        if to_update:
            self.update_all_btn.setText(f"Update All ({len(to_update)})")
            self.update_all_btn.show()
        else:
            self.update_all_btn.hide()