import sys
import os
import mimetypes
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QToolButton, QMenu, QAction, QFileSystemWatcher, 
                             QGraphicsOpacityEffect, QLabel, QStyleFactory)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, pyqtProperty
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBitmap, QFont

class AnimatedButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scale = 1.0
        self.setFixedSize(64, 64)
        self.setIconSize(self.size() * 0.6)
        self.setStyleSheet("""
            QToolButton {
                background-color: rgba(255, 255, 255, 0);
                border: none;
                border-radius: 12px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 50);
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)
        
        # Анимация увеличения
        self.anim = QPropertyAnimation(self, b"scale")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutBack)
        
    def enterEvent(self, event):
        self.anim.setStartValue(self._scale)
        self.anim.setEndValue(1.3)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.setStartValue(self._scale)
        self.anim.setEndValue(1.0)
        self.anim.start()
        super().leaveEvent(event)

    @pyqtProperty(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        self.updateGeometry()
        # Пересчитываем позицию для центрирования при увеличении
        # В реальном доке тут была бы сложная логика расталкивания соседей
        # Для простоты меняем размер иконки
        new_size = int(64 * value)
        self.setFixedSize(new_size, new_size)
        self.setIconSize(self.size() * 0.6)

class DockWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Основной макет
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)
        self.layout.addStretch()
        
        # Словарь категорий
        self.categories = {
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx"],
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"],
            "Video": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
            "Music": [".mp3", ".wav", ".flac", ".aac"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".html", ".css", ".cpp", ".java", ".sh"],
            "Executables": [".exe", ".msi", ".app", ".deb", ".rpm"],
            "Folders": [] 
        }
        
        self.buttons = {}
        self.watcher = QFileSystemWatcher()
        self.watch_paths = []
        
        # Добавляем стандартные кнопки
        self.add_category_button("Documents", "📄")
        self.add_category_button("Images", "🖼️")
        self.add_category_button("Video", "🎬")
        self.add_category_button("Music", "🎵")
        self.add_category_button("Archives", "📦")
        self.add_category_button("Code", "💻")
        self.add_category_button("Folders", "📁")
        
        self.layout.addStretch()
        
        # Таймер для обновления меню (дебаунс)
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.refresh_menus)
        
        # Мониторинг домашней директории по умолчанию
        home = os.path.expanduser("~")
        if os.path.exists(home):
            self.add_watch_path(home)

        # Перетаскивание
        self.drag_pos = None

    def add_category_button(self, name, emoji):
        btn = AnimatedButton(self)
        btn.setText(emoji)
        btn.setFont(QFont("Segoe UI Emoji", 24)) # Или любой системный шрифт с эмодзи
        btn.setToolTip(name)
        
        menu = QMenu(self)
        btn.setPopupMode(QToolButton.InstantPopup)
        btn.setMenu(menu)
        
        # Контекстное меню для добавления путей
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda pos, n=name: self.show_context_menu(btn, n, pos))
        
        self.buttons[name] = {"button": btn, "menu": menu}
        self.layout.addWidget(btn)
        
        # Подключаем обновление меню перед показом
        menu.aboutToShow.connect(lambda n=name: self.populate_menu(n))

    def show_context_menu(self, btn, category, pos):
        menu = QMenu()
        act = menu.addAction("Добавить папку для мониторинга")
        action = menu.exec_(btn.mapToGlobal(pos))
        if action == act:
            # В реальной версии тут был бы диалог выбора папки
            # Для демо добавим текущую директорию скрипта
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.add_watch_path(script_dir)

    def add_watch_path(self, path):
        if path not in self.watch_paths:
            self.watch_paths.append(path)
            try:
                self.watcher.addPath(path)
                print(f"Watching: {path}")
            except Exception as e:
                print(f"Error watching {path}: {e}")
            
            # Подключаем сигналы
            # Используем универсальный подход для совместимости
            try:
                self.watcher.directoryChanged.connect(self.on_directory_changed)
            except AttributeError:
                pass # Fallback logic if needed
            
            self.schedule_refresh()

    def on_directory_changed(self, path):
        self.schedule_refresh()
        # Переподписываемся, т.к. watcher иногда снимает подписку при изменении
        if path in self.watch_paths and path not in self.watcher.directories():
             try:
                 self.watcher.addPath(path)
             except: pass

    def schedule_refresh(self):
        if not self.update_timer.isActive():
            self.update_timer.start(500)

    def populate_menu(self, category_name):
        menu = self.buttons[category_name]["menu"]
        menu.clear()
        
        files_found = False
        
        for path in self.watch_paths:
            if not os.path.exists(path):
                continue
                
            try:
                items = os.listdir(path)
            except PermissionError:
                continue

            for item in items:
                full_path = os.path.join(path, item)
                
                is_folder = os.path.isdir(full_path)
                
                # Логика распределения
                should_add = False
                if category_name == "Folders" and is_folder:
                    should_add = True
                elif not is_folder:
                    ext = os.path.splitext(item)[1].lower()
                    if category_name in self.categories:
                        if ext in self.categories[category_name]:
                            should_add = True
                    if category_name == "Executables" and (ext == "" or (os.name == 'nt' and ext == '.exe')):
                         # Простая эвристика для исполняемых файлов без расширения или .exe
                         if os.access(full_path, os.X_OK) or ext == '.exe':
                             should_add = True

                if should_add:
                    files_found = True
                    action = QAction(item[:30] + "..." if len(item) > 30 else item, self)
                    action.triggered.connect(lambda checked, p=full_path: self.open_item(p))
                    menu.addAction(action)
        
        if not files_found:
            action = QAction("Нет файлов", self)
            action.setEnabled(False)
            menu.addAction(action)

    def refresh_menus(self):
        # Просто триггерим обновление всех меню при изменении
        pass 

    def open_item(self, path):
        try:
            os.startfile(path) if os.name == 'nt' else os.system(f'open "{path}"' if sys.platform == 'darwin' else f'xdg-open "{path}"')
        except Exception as e:
            print(f"Error opening {path}: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            # Правый клик по виджету - выход или настройки
            menu = QMenu()
            menu.addAction("Скрыть").triggered.connect(self.hide)
            menu.addAction("Выход").triggered.connect(qApp.quit)
            menu.exec_(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.hide()
            # Показываем снова по клику в трей или таймеру (упрощено)
            QTimer.singleShot(2000, self.show)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Стиль для всего приложения
    app.setStyle(QStyleFactory.create("Fusion"))
    
    widget = DockWidget()
    widget.show()
    
    # Центрируем сверху экрана
    screen = app.primaryScreen().geometry()
    widget.move(screen.center().x() - widget.width() // 2, 50)
    
    sys.exit(app.exec_())
