# -*- coding: utf-8 -*-
# ウィンドウサイズとテキストの基準フォントサイズ
WINDOW_SIZE = (870, 236)
TEXT_FONT_SIZE = 20
BUTTON_FONT_SIZE = 17

import datetime
import os
import sys

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QCursor, QFont, QGuiApplication, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Windowsのファイル名で禁止されている文字セット
INVALID_CHARS = set('\\/:*?"<>|')
# 全角空白と全角アンダースコア
FULLWIDTH_SPACE = "\u3000"
FULLWIDTH_UNDERSCORE = "\uff3f"
TEXT_VISIBLE_LINES = 4


class PathTextEdit(QPlainTextEdit):
    # DnD受け取り用の入力欄
    def __init__(self, on_drop_callback, on_enter_callback=None, parent=None):
        super().__init__(parent)
        self._on_drop_callback = on_drop_callback
        self._on_enter_callback = on_enter_callback
        self.setAcceptDrops(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

    def keyPressEvent(self, event):
        # 禁止文字の直接入力をブロック
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._on_enter_callback:
                self._on_enter_callback()
            event.accept()
            return

        if event.key() == Qt.Key.Key_Tab:
            event.ignore()
            return

        text = event.text()
        if text and any(ch in INVALID_CHARS or ch in ("\r", "\n", "\t") for ch in text):
            event.ignore()
            return
        super().keyPressEvent(event)

    def canInsertFromMimeData(self, source):
        # ローカルファイルのDnDのみ独自処理し、それ以外は既定の貼り付け/ドロップへ委譲
        if self._extract_local_file_path(source):
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        # QPlainTextEditの標準DnD状態管理を維持したまま、ファイルドロップだけ読込に置き換える
        path = self._extract_local_file_path(source)
        if not path:
            super().insertFromMimeData(source)
            return

        self._on_drop_callback(path)
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    @staticmethod
    def _extract_local_file_path(mime_data):
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    return url.toLocalFile()
        return None


class RenameMateWindow(QWidget):
    # メインウィンドウ
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RenameMate v1.5.1")
        self.setFixedSize(*WINDOW_SIZE)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        # 現在選択中のパスと状態
        self.current_path = None
        self._in_text_change = False

        # ベース名と拡張子の入力欄
        self.base_text = PathTextEdit(self.load_path, self.on_rename_clear_minimize, self)
        self.ext_text = PathTextEdit(self.load_path, self.on_rename_clear_minimize, self)
        self.base_text.textChanged.connect(self.on_text_sanitize)
        self.ext_text.textChanged.connect(self.on_text_sanitize)
        self._apply_text_font()

        # ボタン設定
        button_font = QFont()
        button_font.setPointSize(BUTTON_FONT_SIZE)
        button_size = (80, 45)          # 標準ボタンのサイズ
        combo_button_size = (220, 45)   # 追加ボタンのみ横幅を広くする

        # 操作ボタン
        self.rename_clear_minimize_button = QPushButton("変更&&クリア&&最小化", self)
        self.rename_button = QPushButton("変更", self)
        self.clear_button = QPushButton("クリア", self)
        self.prefix_date_button = QPushButton("日付_", self)
        self.suffix_date_button = QPushButton("_日付", self)
        self.space_button = QPushButton("\" \">_", self)

        self.rename_clear_minimize_button.setFont(button_font)
        self.rename_clear_minimize_button.setMinimumSize(*combo_button_size)

        for btn in (
            self.rename_button,
            self.clear_button,
            self.prefix_date_button,
            self.suffix_date_button,
            self.space_button,
        ):
            btn.setFont(button_font)
            btn.setMinimumSize(*button_size)

        # 常に手前に表示するチェックボックス
        self.always_on_top = QCheckBox("常に手前に表示", self)
        self.always_on_top.setChecked(True)

        # イベントバインド
        self.rename_clear_minimize_button.clicked.connect(self.on_rename_clear_minimize)
        self.rename_button.clicked.connect(self.on_rename)
        self.clear_button.clicked.connect(self.on_clear)
        self.prefix_date_button.clicked.connect(self.on_prefix_date)
        self.suffix_date_button.clicked.connect(self.on_suffix_date)
        self.space_button.clicked.connect(self.on_replace_spaces)
        self.always_on_top.stateChanged.connect(self.on_toggle_topmost)

        # レイアウト
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        text_layout = QHBoxLayout()
        text_layout.setSpacing(10)
        text_layout.addWidget(self.base_text, 3)
        text_layout.addWidget(self.ext_text, 1)
        main_layout.addLayout(text_layout, 1)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addWidget(self.rename_clear_minimize_button)
        button_layout.addWidget(self.rename_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.prefix_date_button)
        button_layout.addWidget(self.suffix_date_button)
        button_layout.addWidget(self.space_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.always_on_top, 0, Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(button_layout)

        self._center_window()

    def _center_window(self):
        # 初期位置は画面中央
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        bounds = screen.availableGeometry()
        x = bounds.x() + (bounds.width() - self.width()) // 2
        y = bounds.y() + (bounds.height() - self.height()) // 2
        self.move(x, y)

    def _apply_text_font(self):
        # テキストボックスへフォント反映
        font = QFont(self.base_text.font())
        font.setPointSize(TEXT_FONT_SIZE)
        self.base_text.setFont(font)
        self.ext_text.setFont(font)
        self._apply_text_box_height()
        self.base_text.update()
        self.ext_text.update()

    def _apply_text_box_height(self):
        # テキスト入力欄の高さを4行分に固定
        for ctrl in (self.base_text, self.ext_text):
            line_height = ctrl.fontMetrics().lineSpacing() * TEXT_VISIBLE_LINES
            frame = ctrl.frameWidth() * 2
            doc_margin = int(ctrl.document().documentMargin() * 2)
            margins = ctrl.contentsMargins()
            height = line_height + frame + doc_margin + margins.top() + margins.bottom()
            ctrl.setFixedHeight(height)

    def changeEvent(self, event):
        # 最小化解除時にカーソル付近へ移動
        if event.type() == QEvent.Type.WindowStateChange:
            old_state = event.oldState()
            was_minimized = bool(old_state & Qt.WindowState.WindowMinimized)
            is_minimized = bool(self.windowState() & Qt.WindowState.WindowMinimized)
            if was_minimized and not is_minimized:
                self.position_near_cursor()
        super().changeEvent(event)

    def on_text_sanitize(self):
        # 貼り付け等で混入した禁止文字を除去
        if self._in_text_change:
            return

        ctrl = self.sender()
        value = ctrl.toPlainText()
        sanitized = self._sanitize_text(value)
        if sanitized != value:
            self._in_text_change = True
            cursor = ctrl.textCursor()
            pos = cursor.position()
            ctrl.setPlainText(sanitized)
            cursor = ctrl.textCursor()
            cursor.setPosition(min(pos, len(sanitized)))
            ctrl.setTextCursor(cursor)
            self._in_text_change = False

    def _sanitize_text(self, text):
        # Windowsファイル名で禁止される文字を取り除く
        cleaned = []
        for char in text:
            if char in INVALID_CHARS:
                continue
            if char in ("\r", "\n", "\t"):
                continue
            cleaned.append(char)
        return "".join(cleaned)

    def load_path(self, path):
        # ドロップされたパスからベース名と拡張子を分解
        if not os.path.exists(path):
            self._show_message("指定されたパスが見つかりません。", QMessageBox.Icon.Critical)
            return

        self.current_path = path
        name = os.path.basename(path)
        base, ext = os.path.splitext(name)
        if ext.startswith("."):
            ext = ext[1:]

        self.base_text.setPlainText(base)
        self.ext_text.setPlainText(ext)

    def on_prefix_date(self):
        # 先頭に日付を追加
        date_str = datetime.datetime.now().strftime("%y%m%d_")
        self.base_text.setPlainText(date_str + self.base_text.toPlainText())

    def on_suffix_date(self):
        # 末尾に日付を追加
        date_str = datetime.datetime.now().strftime("%y%m%d")
        self.base_text.setPlainText(self.base_text.toPlainText() + "_" + date_str)

    def on_replace_spaces(self):
        # 空白の置換（半角→_、全角→＿）
        value = self.base_text.toPlainText()
        value = value.replace(" ", "_")
        value = value.replace(FULLWIDTH_SPACE, FULLWIDTH_UNDERSCORE)
        self.base_text.setPlainText(value)

    def on_clear(self):
        # 入力欄と対象パスをリセット
        self.current_path = None
        self.base_text.clear()
        self.ext_text.clear()
        self.base_text.setFocus()

    def on_rename(self):
        # 実際のリネーム処理
        self._rename_current()

    def on_rename_clear_minimize(self):
        # 変更→クリア→最小化を一括で実行
        if not self.current_path:
            self.showMinimized()
            return

        if not self._rename_current():
            return
        self.on_clear()
        self.showMinimized()

    def _rename_current(self):
        # 現在の入力内容でリネームを実行
        if not self.current_path:
            self._show_message("オブジェクトをドラッグ＆ドロップしてください。", QMessageBox.Icon.Information)
            return False

        base = self._sanitize_text(self.base_text.toPlainText()).strip()
        ext = self._sanitize_text(self.ext_text.toPlainText()).strip()

        if not base:
            self._show_message("ベース名が空です。", QMessageBox.Icon.Critical)
            return False

        if ext and not ext.startswith("."):
            ext = "." + ext
        new_name = base + ext

        src_dir = os.path.dirname(self.current_path)
        new_path = os.path.join(src_dir, new_name)

        if os.path.normcase(new_path) == os.path.normcase(self.current_path):
            return True

        if os.path.exists(new_path):
            self._show_message("同じ名前のオブジェクトが既に存在します。", QMessageBox.Icon.Critical)
            return False

        try:
            os.rename(self.current_path, new_path)
        except OSError as exc:
            self._show_message(f"変更に失敗しました: {exc}", QMessageBox.Icon.Critical)
            return False

        self.current_path = new_path
        # 成功時はポップアップを出さずに状態のみ更新
        return True

    def on_toggle_topmost(self, state):
        # 常に手前表示の切り替え
        on_top = state == Qt.CheckState.Checked.value
        was_minimized = self.isMinimized()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        self.show()
        if was_minimized:
            self.showMinimized()
        else:
            self.raise_()
            self.activateWindow()

    def _show_message(self, message, icon):
        # 必要なときだけメッセージ表示
        message_box = QMessageBox(self)
        message_box.setWindowTitle("RenameMate")
        message_box.setText(message)
        message_box.setIcon(icon)
        message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        message_box.exec()

    def position_near_cursor(self):
        # カーソル付近に表示し、画面外にはみ出さないよう補正
        mouse_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(mouse_pos)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        bounds = screen.availableGeometry()
        width = self.frameGeometry().width()
        height = self.frameGeometry().height()

        # 少しオフセットしてカーソルと被らないようにする
        x = mouse_pos.x() + 10
        y = mouse_pos.y() + 10

        max_x = bounds.x() + bounds.width() - width
        max_y = bounds.y() + bounds.height() - height

        if max_x < bounds.x():
            x = bounds.x()
        else:
            x = min(max(x, bounds.x()), max_x)

        if max_y < bounds.y():
            y = bounds.y()
        else:
            y = min(max(y, bounds.y()), max_y)

        self.move(x, y)


class RenameMateApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.frame = RenameMateWindow()
        self.frame.position_near_cursor()
        self.frame.show()

        # コマンドライン引数で渡されたパスを読み込む（右クリック連携用）
        start_path = self._get_start_path()
        if start_path:
            self.frame.load_path(start_path)

    def _get_start_path(self):
        # 右クリックの旧コンテキストメニューから渡される "%1" を想定
        if len(sys.argv) < 2:
            return None
        return sys.argv[1]


if __name__ == "__main__":
    # エントリーポイント
    app = RenameMateApp(sys.argv)
    sys.exit(app.exec())
