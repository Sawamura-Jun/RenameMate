# -*- coding: utf-8 -*-
# ウィンドウサイズとテキストの基準フォントサイズ
WINDOW_SIZE = (880, 260)
TEXT_FONT_SIZE = 24

import datetime
import os
import sys

import wx

# Windowsのファイル名で禁止されている文字セット
INVALID_CHARS = set('\\/:*?"<>|')
# 全角空白と全角アンダースコア
FULLWIDTH_SPACE = "\u3000"
FULLWIDTH_UNDERSCORE = "\uff3f"


class RenameMateDropTarget(wx.FileDropTarget):
    # DnD受け取り用のドロップターゲット
    def __init__(self, on_drop_callback):
        super().__init__()
        self.on_drop_callback = on_drop_callback

    def OnDropFiles(self, x, y, filenames):
        # ドロップされた先頭1件のみを扱う
        if not filenames:
            return False
        self.on_drop_callback(filenames[0])
        return True


class RenameMateFrame(wx.Frame):
    # メインウィンドウ
    def __init__(self):
        # 常に手前表示の初期スタイル
        style = wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP
        super().__init__(None, title="RenameMate", size=WINDOW_SIZE, style=style)

        # 現在選択中のパスと状態
        self.current_path = None
        self.text_font_size = TEXT_FONT_SIZE
        self._in_text_change = False

        # ルートパネル
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(150, 150, 150))

        # ベース名と拡張子の入力欄
        self.base_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        self.ext_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        self._apply_text_font()

        # DnDの受付
        self.base_text.SetDropTarget(RenameMateDropTarget(self.load_path))
        self.ext_text.SetDropTarget(RenameMateDropTarget(self.load_path))

        # 禁止文字のフィルタとサニタイズ
        self.base_text.Bind(wx.EVT_CHAR, self.on_char_filter)
        self.ext_text.Bind(wx.EVT_CHAR, self.on_char_filter)
        self.base_text.Bind(wx.EVT_TEXT, self.on_text_sanitize)
        self.ext_text.Bind(wx.EVT_TEXT, self.on_text_sanitize)

        # Ctrl + ホイールで文字サイズ変更
        self.base_text.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.ext_text.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        panel.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        # Ctrl+0 で文字サイズをデフォルトに戻す
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)
        # 最小化/復元時の位置調整
        self.Bind(wx.EVT_ICONIZE, self.on_iconize)

        # ボタン設定
        button_font = wx.Font(17, wx.FONTFAMILY_DEFAULT,
                              wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        button_size = (80, 45)     # 標準ボタンのサイズ
        combo_button_size = (220, 45)  # 追加ボタンのみ横幅を広くする

        # 操作ボタン
        self.rename_clear_minimize_button = wx.Button(panel, label="変更&&クリア&&最小化")
        self.rename_button = wx.Button(panel, label="変更")
        self.clear_button = wx.Button(panel, label="クリア")
        self.prefix_date_button = wx.Button(panel, label="日付_")
        self.suffix_date_button = wx.Button(panel, label="_日付")
        self.space_button = wx.Button(panel, label="\" \">_")

        self.rename_clear_minimize_button.SetFont(button_font)
        self.rename_clear_minimize_button.SetMinSize(combo_button_size)

        for btn in (self.rename_button, self.clear_button, self.prefix_date_button,
                    self.suffix_date_button, self.space_button):
            btn.SetFont(button_font)
            btn.SetMinSize(button_size)

        # 常に手前に表示するチェックボックス
        self.always_on_top = wx.CheckBox(panel, label="常に手前に表示")
        self.always_on_top.SetValue(True)

        # イベントバインド
        self.rename_clear_minimize_button.Bind(wx.EVT_BUTTON, self.on_rename_clear_minimize)
        self.rename_button.Bind(wx.EVT_BUTTON, self.on_rename)
        self.clear_button.Bind(wx.EVT_BUTTON, self.on_clear)
        self.prefix_date_button.Bind(wx.EVT_BUTTON, self.on_prefix_date)
        self.suffix_date_button.Bind(wx.EVT_BUTTON, self.on_suffix_date)
        self.space_button.Bind(wx.EVT_BUTTON, self.on_replace_spaces)
        self.always_on_top.Bind(wx.EVT_CHECKBOX, self.on_toggle_topmost)

        # レイアウト
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer = wx.BoxSizer(wx.HORIZONTAL)
        text_sizer.Add(self.base_text, 3, wx.LEFT | wx.TOP | wx.EXPAND, 10)
        text_sizer.AddSpacer(10)
        text_sizer.Add(self.ext_text, 1, wx.RIGHT | wx.TOP | wx.EXPAND, 10)
        main_sizer.Add(text_sizer, 1, wx.EXPAND)
        main_sizer.AddSpacer(10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.rename_clear_minimize_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.Add(self.rename_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.Add(self.clear_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.Add(self.prefix_date_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.Add(self.suffix_date_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.Add(self.space_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(self.always_on_top, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 5)

        main_sizer.Add(button_sizer, 0, wx.EXPAND)

        panel.SetSizer(main_sizer)
        self.Centre()

    def _apply_text_font(self):
        # テキストボックスへフォント反映
        font = wx.Font(self.text_font_size, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.base_text.SetFont(font)
        self.ext_text.SetFont(font)
        self.base_text.Refresh()
        self.ext_text.Refresh()

    def on_mouse_wheel(self, event):
        # Ctrl+ホイールで文字サイズを変更
        if event.ControlDown():
            rotation = event.GetWheelRotation()
            if rotation > 0:
                self.text_font_size += 1
            elif rotation < 0:
                self.text_font_size -= 1
            self.text_font_size = max(6, min(self.text_font_size, 72))
            self._apply_text_font()
        else:
            event.Skip()

    def on_char_hook(self, event):
        # Ctrl+0 で文字サイズを初期値に戻す
        key_code = event.GetKeyCode()
        if event.ControlDown() and key_code in (ord("0"), wx.WXK_NUMPAD0):
            self.text_font_size = TEXT_FONT_SIZE
            self._apply_text_font()
            return
        event.Skip()

    def on_iconize(self, event):
        # 最小化解除時にカーソル付近へ移動
        if not event.IsIconized():
            self.position_near_cursor()
        event.Skip()

    def on_char_filter(self, event):
        # 禁止文字の入力をブロック
        key_code = event.GetUnicodeKey()
        if key_code == wx.WXK_NONE:
            key_code = event.GetKeyCode()

        if key_code < 32:
            event.Skip()
            return

        try:
            char = chr(key_code)
        except ValueError:
            event.Skip()
            return

        if char in INVALID_CHARS or char in ("\r", "\n", "\t"):
            return

        event.Skip()

    def on_text_sanitize(self, event):
        # 貼り付け等で混入した禁止文字を除去
        if self._in_text_change:
            return

        ctrl = event.GetEventObject()
        value = ctrl.GetValue()
        sanitized = self._sanitize_text(value)
        if sanitized != value:
            self._in_text_change = True
            pos = ctrl.GetInsertionPoint()
            ctrl.ChangeValue(sanitized)
            ctrl.SetInsertionPoint(min(pos, len(sanitized)))
            self._in_text_change = False

        event.Skip()

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
            self._show_message("指定されたパスが見つかりません。", wx.ICON_ERROR)
            return

        self.current_path = path
        name = os.path.basename(path)
        base, ext = os.path.splitext(name)
        if ext.startswith("."):
            ext = ext[1:]

        self.base_text.ChangeValue(base)
        self.ext_text.ChangeValue(ext)

    def on_prefix_date(self, event):
        # 先頭に日付を追加
        date_str = datetime.datetime.now().strftime("%y%m%d_")
        self.base_text.ChangeValue(date_str + self.base_text.GetValue())

    def on_suffix_date(self, event):
        # 末尾に日付を追加
        date_str = datetime.datetime.now().strftime("%y%m%d")
        self.base_text.ChangeValue(self.base_text.GetValue() + "_" + date_str)

    def on_replace_spaces(self, event):
        # 空白の置換（半角→_、全角→＿）
        value = self.base_text.GetValue()
        value = value.replace(" ", "_")
        value = value.replace(FULLWIDTH_SPACE, FULLWIDTH_UNDERSCORE)
        self.base_text.ChangeValue(value)

    def on_clear(self, event):
        # 入力欄と対象パスをリセット
        self.current_path = None
        self.base_text.ChangeValue("")
        self.ext_text.ChangeValue("")
        self.base_text.SetFocus()

    def on_rename(self, event):
        # 実際のリネーム処理
        self._rename_current()

    def on_rename_clear_minimize(self, event):
        # 変更→クリア→最小化を一括で実行
        if not self._rename_current():
            return
        self.on_clear(None)
        self.Iconize(True)

    def _rename_current(self):
        # 現在の入力内容でリネームを実行
        if not self.current_path:
            self._show_message("オブジェクトをドラッグ＆ドロップしてください。", wx.ICON_INFORMATION)
            return False

        base = self._sanitize_text(self.base_text.GetValue()).strip()
        ext = self._sanitize_text(self.ext_text.GetValue()).strip()

        if not base:
            self._show_message("ベース名が空です。", wx.ICON_ERROR)
            return False

        if ext:
            if not ext.startswith("."):
                ext = "." + ext
        new_name = base + ext

        src_dir = os.path.dirname(self.current_path)
        new_path = os.path.join(src_dir, new_name)

        if os.path.normcase(new_path) == os.path.normcase(self.current_path):
            return True

        if os.path.exists(new_path):
            self._show_message("同じ名前のオブジェクトが既に存在します。", wx.ICON_ERROR)
            return False

        try:
            os.rename(self.current_path, new_path)
        except OSError as exc:
            self._show_message(f"変更に失敗しました: {exc}", wx.ICON_ERROR)
            return False

        self.current_path = new_path
        # 成功時はポップアップを出さずに状態のみ更新
        return True

    def on_toggle_topmost(self, event):
        # 常に手前表示の切り替え
        style = self.GetWindowStyle()
        if event.IsChecked():
            style |= wx.STAY_ON_TOP
        else:
            style &= ~wx.STAY_ON_TOP
        self.SetWindowStyleFlag(style)
        self.Raise()

    def _show_message(self, message, icon):
        # 必要なときだけメッセージ表示
        wx.MessageBox(message, "RenameMate", wx.OK | icon)

    def position_near_cursor(self):
        # カーソル付近に表示し、画面外にはみ出さないよう補正
        mouse_pos = wx.GetMousePosition()
        display_index = wx.Display.GetFromPoint(mouse_pos)
        if display_index == wx.NOT_FOUND:
            display = wx.Display(0)
        else:
            display = wx.Display(display_index)

        bounds = display.GetGeometry()
        size = self.GetSize()

        # 少しオフセットしてカーソルと被らないようにする
        x = mouse_pos.x + 10
        y = mouse_pos.y + 10

        max_x = bounds.x + bounds.width - size.x
        max_y = bounds.y + bounds.height - size.y

        x = min(max(x, bounds.x), max_x)
        y = min(max(y, bounds.y), max_y)

        self.SetPosition(wx.Point(x, y))


class RenameMateApp(wx.App):
    def OnInit(self):
        # アプリ起動時にフレームを生成
        frame = RenameMateFrame()
        frame.position_near_cursor()
        frame.Show()
        frame.Refresh()
        # コマンドライン引数で渡されたパスを読み込む（右クリック連携用）
        start_path = self._get_start_path()
        if start_path:
            frame.load_path(start_path)
        return True

    def _get_start_path(self):
        # 右クリックの旧コンテキストメニューから渡される "%1" を想定
        if len(sys.argv) < 2:
            return None
        return sys.argv[1]


if __name__ == "__main__":
    # エントリーポイント
    app = RenameMateApp()
    app.MainLoop()
