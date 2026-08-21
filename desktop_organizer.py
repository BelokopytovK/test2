#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Desktop Organizer Application
Компонует ярлыки, папки и файлы в выпадающие меню на рабочем столе.
"""

import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu, QAction, 
    QFileDialog, QMessageBox, QLabel, QVBoxLayout, QPushButton,
    QDialog, QListWidget, QListWidgetItem, QDialogButtonBox, QHBoxLayout
)
from PyQt5.QtGui import QIcon, QPixmap, QCursor
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer


class SettingsDialog(QDialog):
    """Диалог настройки отслеживаемых папок."""
    
    def __init__(self, folders, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки папок")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Список папок
        self.folder_list = QListWidget()
        for folder in folders:
            self.folder_list.addItem(folder)
        layout.addWidget(self.folder_list)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Добавить папку")
        add_btn.clicked.connect(self.add_folder)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Удалить выбранное")
        remove_btn.clicked.connect(self.remove_folder)
        btn_layout.addWidget(remove_btn)
        
        layout.addLayout(btn_layout)
        
        # Кнопки OK/Cancel
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
    
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку для отслеживания"
        )
        if folder and folder not in self.get_folders():
            self.folder_list.addItem(folder)
    
    def remove_folder(self):
        current = self.folder_list.currentRow()
        if current >= 0:
            self.folder_list.takeItem(current)
    
    def get_folders(self):
        return [
            self.folder_list.item(i).text() 
            for i in range(self.folder_list.count())
        ]


class DesktopOrganizer(QWidget):
    """Основное приложение организатора рабочего стола."""
    
    def __init__(self):
        super().__init__()
        
        # Конфигурация
        self.config_file = Path.home() / ".desktop_organizer.conf"
        self.watched_folders = self.load_config()
        
        # Если папок нет, добавляем стандартные
        if not self.watched_folders:
            desktop = Path.home() / "Desktop"
            if desktop.exists():
                self.watched_folders = [str(desktop)]
            else:
                self.watched_folders = [str(Path.home())]
        
        # Инициализация системного трея
        self.tray_icon = None
        self.context_menu = None
        self.file_menus = {}  # Хранение меню для файлов
        
        self.init_ui()
        self.init_tray()
        self.update_menu()
        
        # Мониторинг файловой системы
        self.fs_watcher = QFileSystemWatcher()
        self.fs_watcher.directoriesChanged.connect(self.on_directory_changed)
        self.update_watcher()
        
        # Таймер для периодического обновления
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_menu)
        self.timer.start(5000)  # Обновление каждые 5 секунд
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса."""
        self.setWindowFlags(Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Desktop Organizer запущен\nПроверьте системный трей")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 200);
                color: white;
                padding: 20px;
                border-radius: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(label)
        
        self.resize(300, 100)
        self.move(
            QApplication.primaryScreen().geometry().center() - self.rect().center()
        )
    
    def init_tray(self):
        """Инициализация иконки в системном трее."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(
                self, "Ошибка", "Системный трей недоступен"
            )
            sys.exit(1)
        
        self.context_menu = QMenu()
        
        # Создаем иконку (простой цветной квадрат)
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.blue)
        icon = QIcon(pixmap)
        
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setContextMenu(self.context_menu)
        self.tray_icon.setToolTip("Desktop Organizer")
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
    
    def load_config(self):
        """Загрузка конфигурации из файла."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f if line.strip()]
            except Exception:
                pass
        return []
    
    def save_config(self):
        """Сохранение конфигурации в файл."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                for folder in self.watched_folders:
                    f.write(folder + '\n')
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {e}")
    
    def update_watcher(self):
        """Обновление мониторинга файловой системы."""
        current_watched = self.fs_watcher.directories()
        
        # Удаляем старые пути
        for path in current_watched:
            if path not in self.watched_folders:
                self.fs_watcher.removePath(path)
        
        # Добавляем новые пути
        for path in self.watched_folders:
            if path not in current_watched and os.path.isdir(path):
                self.fs_watcher.addPath(path)
    
    def on_directory_changed(self, path):
        """Обработчик изменений в директории."""
        self.update_menu()
    
    def on_tray_activated(self, reason):
        """Обработчик активации иконки в трее."""
        if reason == QSystemTrayIcon.Trigger:
            self.update_menu()
            self.context_menu.popup(QCursor.pos())
    
    def get_file_icon(self, filepath):
        """Определение типа файла и возвращение соответствующей иконки."""
        ext = Path(filepath).suffix.lower()
        
        # Иконки для разных типов файлов
        icons = {
            '.lnk': '📌',  # Ярлык
            '.exe': '⚙️',  # Приложение
            '.txt': '📄',  # Текст
            '.doc': '📝', '.docx': '📝',
            '.pdf': '📕',
            '.xls': '📊', '.xlsx': '📊',
            '.ppt': '📽️', '.pptx': '📽️',
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
            '.mp3': '🎵', '.wav': '🎵',
            '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬',
            '.zip': '📦', '.rar': '📦', '.7z': '📦',
            '.py': '🐍', '.js': '🌐', '.html': '🌐', '.css': '🎨',
        }
        
        return icons.get(ext, '📁' if os.path.isdir(filepath) else '📄')
    
    def categorize_files(self, filepath):
        """Категоризация файлов по типам."""
        if os.path.isdir(filepath):
            return 'Папки'
        
        ext = Path(filepath).suffix.lower()
        
        categories = {
            'Ярлыки': ['.lnk', '.url'],
            'Документы': ['.txt', '.doc', '.docx', '.pdf', '.odt', '.rtf'],
            'Таблицы': ['.xls', '.xlsx', '.csv', '.ods'],
            'Презентации': ['.ppt', '.pptx', '.odp'],
            'Изображения': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
            'Видео': ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
            'Аудио': ['.mp3', '.wav', '.flac', '.aac', '.ogg'],
            'Архивы': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'Приложения': ['.exe', '.msi', '.bat', '.cmd', '.sh'],
            'Код': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c'],
        }
        
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        
        return 'Разное'
    
    def update_menu(self):
        """Обновление контекстного меню."""
        if not self.context_menu:
            return
        
        self.context_menu.clear()
        
        # Заголовок
        title_action = QAction("🗂️ Desktop Organizer", self.context_menu)
        title_action.setEnabled(False)
        self.context_menu.addAction(title_action)
        self.context_menu.addSeparator()
        
        # Сбор всех файлов из отслеживаемых папок
        all_files = {}  # category -> [(name, path, is_dir)]
        
        for folder in self.watched_folders:
            if not os.path.isdir(folder):
                continue
            
            try:
                for item in os.listdir(folder):
                    filepath = os.path.join(folder, item)
                    category = self.categorize_files(filepath)
                    
                    if category not in all_files:
                        all_files[category] = []
                    
                    icon = self.get_file_icon(filepath)
                    is_dir = os.path.isdir(filepath)
                    all_files[category].append((f"{icon} {item}", filepath, is_dir))
            
            except PermissionError:
                continue
        
        # Создание подменю для каждой категории
        for category in sorted(all_files.keys()):
            files = all_files[category]
            
            if len(files) <= 10:
                # Если файлов мало, создаем простое подменю
                category_menu = self.context_menu.addMenu(f"📁 {category}")
                
                for name, filepath, is_dir in sorted(files):
                    action = QAction(name, self.context_menu)
                    action.triggered.connect(
                        lambda checked, p=filepath: self.open_item(p)
                    )
                    category_menu.addAction(action)
                
                category_menu.addSeparator()
                open_folder_action = QAction(f"Открыть папку", category_menu)
                folder_path = os.path.dirname(filepath) if not is_dir else filepath
                open_folder_action.triggered.connect(
                    lambda checked, p=folder_path: self.open_item(p)
                )
                category_menu.addAction(open_folder_action)
            else:
                # Если файлов много, создаем алфавитное подменю
                category_menu = self.context_menu.addMenu(f"📁 {category} ({len(files)})")
                
                # Группировка по буквам
                by_letter = {}
                for name, filepath, is_dir in files:
                    letter = name[0].upper() if name else '#'
                    if not letter.isalpha():
                        letter = '#'
                    if letter not in by_letter:
                        by_letter[letter] = []
                    by_letter[letter].append((name, filepath, is_dir))
                
                for letter in sorted(by_letter.keys()):
                    letter_menu = category_menu.addMenu(letter)
                    for name, filepath, is_dir in sorted(by_letter[letter]):
                        action = QAction(name, category_menu)
                        action.triggered.connect(
                            lambda checked, p=filepath: self.open_item(p)
                        )
                        letter_menu.addAction(action)
        
        self.context_menu.addSeparator()
        
        # Действия управления
        settings_action = QAction("⚙️ Настройки папок", self.context_menu)
        settings_action.triggered.connect(self.show_settings)
        self.context_menu.addAction(settings_action)
        
        refresh_action = QAction("🔄 Обновить", self.context_menu)
        refresh_action.triggered.connect(self.update_menu)
        self.context_menu.addAction(refresh_action)
        
        self.context_menu.addSeparator()
        
        quit_action = QAction("❌ Выход", self.context_menu)
        quit_action.triggered.connect(self.quit_app)
        self.context_menu.addAction(quit_action)
    
    def open_item(self, filepath):
        """Открытие файла или папки."""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
            elif os.name == 'posix':  # Linux/Mac
                import subprocess
                subprocess.call(['xdg-open', filepath])
            else:
                QMessageBox.warning(
                    self, "Ошибка", f"Неподдерживаемая ОС для открытия файлов"
                )
        except Exception as e:
            QMessageBox.warning(
                self, "Ошибка", f"Не удалось открыть: {filepath}\n{e}"
            )
    
    def show_settings(self):
        """Показ диалога настроек."""
        dialog = SettingsDialog(self.watched_folders, self)
        if dialog.exec_() == QDialog.Accepted:
            self.watched_folders = dialog.get_folders()
            self.save_config()
            self.update_watcher()
            self.update_menu()
    
    def quit_app(self):
        """Выход из приложения."""
        self.tray_icon.hide()
        QApplication.quit()


if __name__ == "__main__":
    # Исправление для запуска от имени администратора в Windows
    if os.name == 'nt':
        import ctypes
        try:
            ctypes.windll.shell32.IsUserAnAdmin()
        except:
            pass
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    organizer = DesktopOrganizer()
    organizer.show()
    
    # Показываем уведомление
    if organizer.tray_icon:
        organizer.tray_icon.showMessage(
            "Desktop Organizer",
            "Приложение запущено. Щелкните на иконку в трее для доступа к меню.",
            QSystemTrayIcon.Information,
            3000
        )
    
    sys.exit(app.exec_())
