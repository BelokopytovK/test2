import sys
import os
import mimetypes
from collections import defaultdict

# Исправленный импорт: QFileSystemWatcher находится в QtCore, а не в QtWidgets
from PyQt5.QtCore import Qt, QUrl, QFileSystemWatcher, QTimer, QSize
from PyQt5.QtGui import QGuiApplication, QIcon, QFont, QColor, QPainter, QPainterPath
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, qApp, 
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox, QScrollArea, QFrame, QGraphicsOpacityEffect,
    QPropertyAnimation
)

class FileOrganizerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Основные настройки виджета
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)
        self.setGeometry(100, 100, 600, 100)
        
        # Данные
        self.watched_folders = []
        self.file_data = defaultdict(list)
        
        # Инициализация UI
        self.init_ui()
        self.init_watcher()
        
        # Загрузка сохраненных папок
        self.load_settings()
        
        # Таймер для обновления (резервный)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_files)
        self.refresh_timer.start(5000) # Обновление каждые 5 сек

    def init_ui(self):
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(15)
        self.setLayout(self.layout)
        
        # Добавление начальных кнопок категорий
        self.categories = [
            ("📄 Документы", [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"]),
            ("🖼️ Изображения", [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"]),
            ("🎵 Музыка", [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"]),
            ("🎥 Видео", [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"]),
            ("📦 Архивы", [".zip", ".rar", ".7z", ".tar", ".gz"]),
            ("💻 Код", [".py", ".js", ".html", ".css", ".cpp", ".java", ".json", ".xml"]),
            ("⚙️ Программы", [".exe", ".msi", ".bat", ".sh", ".app"]),
            ("📁 Папки", ["folder"])
        ]
        
        self.category_buttons = {}
        
        for name, extensions in self.categories:
            btn = self.create_dock_button(name)
            btn.clicked.connect(lambda checked, n=name: self.show_category_menu(n))
            btn.context_menu_event = lambda event, n=name: self.add_folder_dialog(n)
            self.layout.addWidget(btn)
            self.category_buttons[name] = btn
            
        # Кнопка добавления папки
        add_btn = self.create_dock_button("➕")
        add_btn.clicked.connect(self.add_folder_dialog)
        self.layout.addWidget(add_btn)
        
        # Растягиватель
        self.layout.addStretch()

    def create_dock_button(self, text):
        btn = QPushButton(text)
        btn.setFixedSize(70, 70)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 15px;
                font-size: 24px;
                color: #333;
                border: 2px solid rgba(255, 255, 255, 100);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 240);
                border: 2px solid #fff;
            }
        """)
        
        # Анимация увеличения при наведении
        self.opacity_effect = QGraphicsOpacityEffect()
        btn.setGraphicsEffect(self.opacity_effect)
        
        return btn

    def init_watcher(self):
        self.watcher = QFileSystemWatcher()
        # Используем правильный сигнал directoryChanged вместо directoriesChanged
        if hasattr(self.watcher, 'directoryChanged'):
            self.watcher.directoryChanged.connect(self.on_directory_changed)
        else:
            # Фоллбэк для очень старых версий
            try:
                self.watcher.directoriesChanged.connect(self.on_directory_changed)
            except AttributeError:
                pass

    def load_settings(self):
        # Здесь можно добавить загрузку из конфига, пока просто добавим Рабочий стол
        desktop = os.path.expanduser("~/Desktop")
        if os.path.exists(desktop):
            self.add_watch_folder(desktop)

    def add_watch_folder(self, path):
        if path not in self.watched_folders and os.path.exists(path):
            self.watched_folders.append(path)
            self.watcher.addPath(path)
            self.refresh_files()

    def on_directory_changed(self, path):
        # Небольшая задержка перед обновлением, чтобы файлы успели записаться
        QTimer.singleShot(500, self.refresh_files)

    def refresh_files(self):
        self.file_data.clear()
        
        for folder in self.watched_folders:
            if not os.path.exists(folder):
                continue
            try:
                for item in os.listdir(folder):
                    full_path = os.path.join(folder, item)
                    if os.path.isdir(full_path):
                        self.file_data["📁 Папки"].append({"name": item, "path": full_path})
                    else:
                        ext = os.path.splitext(item)[1].lower()
                        categorized = False
                        for name, extensions in self.categories:
                            if ext in extensions:
                                self.file_data[name].append({"name": item, "path": full_path})
                                categorized = True
                                break
                        if not categorized:
                            self.file_data["📄 Документы"].append({"name": item, "path": full_path})
            except PermissionError:
                pass

    def show_category_menu(self, category_name):
        menu = QMenu(self)
        files = self.file_data.get(category_name, [])
        
        if not files:
            menu.addAction("Пусто")
        else:
            # Сортировка по алфавиту
            files.sort(key=lambda x: x['name'].lower())
            
            for file_info in files[:20]: # Показываем первые 20
                action = QAction(file_info['name'], self)
                action.triggered.connect(lambda checked, p=file_info['path']: self.open_file(p))
                menu.addAction(action)
                
            if len(files) > 20:
                more_action = QAction(f"... еще {len(files) - 20} файлов", self)
                more_action.setEnabled(False)
                menu.addAction(more_action)
        
        menu.exec_(self.mapToGlobal(self.sender().pos()))

    def open_file(self, path):
        os.startfile(path) if sys.platform == 'win32' else QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def add_folder_dialog(self, category=None):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для мониторинга")
        if folder:
            self.add_watch_folder(folder)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_pos'):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Настройка иконки приложения (скрытая)
    app.setQuitOnLastWindowClosed(False)
    
    widget = FileOrganizerWidget()
    widget.show()
    
    sys.exit(app.exec_())
