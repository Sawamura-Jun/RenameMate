# -*- coding: utf-8 -*-
WINDOW_SIZE = (850, 350)
TEXT_FONT_SIZE = 24

import datetime
import os

import wx

INVALID_CHARS = set('\\/:*?"<>|')
FULLWIDTH_SPACE = "\u3000"
FULLWIDTH_UNDERSCORE = "\uff3f"


class RenameMateDropTarget(wx.FileDropTarget):
    def __init__(self, on_drop_callback):
        super().__init__()
        self.on_drop_callback = on_drop_callback

    def OnDropFiles(self, x, y, filenames):
        if not filenames:
            return False
        self.on_drop_callback(filenames[0])
        return True


class RenameMateFrame(wx.Frame):
    def __init__(self):
        style = wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP
        super().__init__(None, title="RenameMate", size=WINDOW_SIZE, style=style)

        self.current_path = None
        self.text_font_size = TEXT_FONT_SIZE
        self._in_text_change = False

        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(150, 150, 150))


        self.base_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        self.ext_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER)
        self._apply_text_font()

        self.base_text.SetDropTarget(RenameMateDropTarget(self.load_path))
        self.ext_text.SetDropTarget(RenameMateDropTarget(self.load_path))

        self.base_text.Bind(wx.EVT_CHAR, self.on_char_filter)
        self.ext_text.Bind(wx.EVT_CHAR, self.on_char_filter)
        self.base_text.Bind(wx.EVT_TEXT, self.on_text_sanitize)
        self.ext_text.Bind(wx.EVT_TEXT, self.on_text_sanitize)

        self.base_text.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        self.ext_text.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        panel.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

        button_font = wx.Font(17, wx.FONTFAMILY_DEFAULT,
                              wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        button_size = (160, 45)

        self.rename_button = wx.Button(panel, label="変更")
        self.prefix_date_button = wx.Button(panel, label="先頭に日付")
        self.suffix_date_button = wx.Button(panel, label="末尾に日付")
        self.space_button = wx.Button(panel, label="空白を_に変更")

        for btn in (self.rename_button, self.prefix_date_button,
                    self.suffix_date_button, self.space_button):
            btn.SetFont(button_font)
            btn.SetMinSize(button_size)

        self.always_on_top = wx.CheckBox(panel, label="常に手前に表示")
        self.always_on_top.SetValue(True)

        self.rename_button.Bind(wx.EVT_BUTTON, self.on_rename)
        self.prefix_date_button.Bind(wx.EVT_BUTTON, self.on_prefix_date)
        self.suffix_date_button.Bind(wx.EVT_BUTTON, self.on_suffix_date)
        self.space_button.Bind(wx.EVT_BUTTON, self.on_replace_spaces)
        self.always_on_top.Bind(wx.EVT_CHECKBOX, self.on_toggle_topmost)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer = wx.BoxSizer(wx.HORIZONTAL)
        text_sizer.Add(self.base_text, 3, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 10)
        text_sizer.Add(self.ext_text, 1, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 10)
        main_sizer.Add(text_sizer, 1, wx.EXPAND)
        main_sizer.AddSpacer(6)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.rename_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.Add(self.prefix_date_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.Add(self.suffix_date_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.Add(self.space_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(self.always_on_top, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, 10)

        main_sizer.Add(button_sizer, 0, wx.EXPAND)

        panel.SetSizer(main_sizer)
        self.Centre()

    def _apply_text_font(self):
        font = wx.Font(self.text_font_size, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.base_text.SetFont(font)
        self.ext_text.SetFont(font)
        self.base_text.Refresh()
        self.ext_text.Refresh()

    def on_mouse_wheel(self, event):
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

    def on_char_filter(self, event):
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
        cleaned = []
        for char in text:
            if char in INVALID_CHARS:
                continue
            if char in ("\r", "\n", "\t"):
                continue
            cleaned.append(char)
        return "".join(cleaned)

    def load_path(self, path):
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
        date_str = datetime.datetime.now().strftime("%y%m%d_")
        self.base_text.ChangeValue(date_str + self.base_text.GetValue())

    def on_suffix_date(self, event):
        date_str = datetime.datetime.now().strftime("%y%m%d")
        self.base_text.ChangeValue(self.base_text.GetValue() + "_" + date_str)

    def on_replace_spaces(self, event):
        value = self.base_text.GetValue()
        value = value.replace(" ", "_")
        value = value.replace(FULLWIDTH_SPACE, FULLWIDTH_UNDERSCORE)
        self.base_text.ChangeValue(value)

    def on_rename(self, event):
        if not self.current_path:
            self._show_message("オブジェクトをドラッグ＆ドロップしてください。", wx.ICON_INFORMATION)
            return

        base = self._sanitize_text(self.base_text.GetValue()).strip()
        ext = self._sanitize_text(self.ext_text.GetValue()).strip()

        if not base:
            self._show_message("ベース名が空です。", wx.ICON_ERROR)
            return

        if ext:
            if not ext.startswith("."):
                ext = "." + ext
        new_name = base + ext

        src_dir = os.path.dirname(self.current_path)
        new_path = os.path.join(src_dir, new_name)

        if os.path.normcase(new_path) == os.path.normcase(self.current_path):
            return

        if os.path.exists(new_path):
            self._show_message("同じ名前のオブジェクトが既に存在します。", wx.ICON_ERROR)
            return

        try:
            os.rename(self.current_path, new_path)
        except OSError as exc:
            self._show_message(f"変更に失敗しました: {exc}", wx.ICON_ERROR)
            return

        self.current_path = new_path
        # Success: update state silently.

    def on_toggle_topmost(self, event):
        style = self.GetWindowStyle()
        if event.IsChecked():
            style |= wx.STAY_ON_TOP
        else:
            style &= ~wx.STAY_ON_TOP
        self.SetWindowStyleFlag(style)
        self.Raise()

    def _show_message(self, message, icon):
        wx.MessageBox(message, "RenameMate", wx.OK | icon)


class RenameMateApp(wx.App):
    def OnInit(self):
        frame = RenameMateFrame()
        frame.Show()
        frame.Refresh()
        return True


if __name__ == "__main__":
    app = RenameMateApp()
    app.MainLoop()
