import wx
import os
import re
import time
import requests
from requests.auth import HTTPProxyAuth
from gui.templates import ScrolledPanel

from gui.ffmpeg_detect import DetectDialog

from utils.config import Config, conf
from utils.tools import get_header
from utils.thread import Thread
from utils.mapping import video_quality_mapping, audio_quality_mapping, video_codec_mapping

class SettingWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "设置")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        self.note = wx.Notebook(self, -1)

        self.note.AddPage(DownloadTab(self.note), "下载")
        self.note.AddPage(MergeTab(self.note), "合成")
        self.note.AddPage(ProxyTab(self.note), "代理")
        self.note.AddPage(MiscTab(self.note), "其他")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.getButtonSize())
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.getButtonSize())

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 0, wx.EXPAND | wx.ALL, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)
    
    def Bind_EVT(self):
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)
    
    def onConfirm(self, event):
        for i in range(0, self.note.GetPageCount()):
            if not self.note.GetPage(i).onConfirm():
                return
            
        event.Skip()

    def getButtonSize(self):
        match Config.Sys.platform:
            case "windows":
                size = self.FromDIP((80, 30))

            case "linux" | "darwin":
                size = self.FromDIP((100, 40))
        
        return size

class DownloadTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        self.download_box = wx.StaticBox(self, -1, "下载设置")

        self.scrolled_panel = ScrolledPanel(self.download_box, self.getPanelSize())

        path_lab = wx.StaticText(self.scrolled_panel, -1, "下载目录")
        self.path_box = wx.TextCtrl(self.scrolled_panel, -1, size = self.FromDIP((220, 24)))
        self.browse_btn = wx.Button(self.scrolled_panel, -1, "浏览", size = self.FromDIP((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        
        self.max_thread_lab = wx.StaticText(self.scrolled_panel, -1, "多线程数：1")
        self.max_thread_slider = wx.Slider(self.scrolled_panel, -1, 1, 1, 8)

        self.max_download_lab = wx.StaticText(self.scrolled_panel, -1, "并行下载数：1")
        max_download = Config.Download.max_download_count if Config.Download.max_download_count > 4 else 4
        self.max_download_slider = wx.Slider(self.scrolled_panel, -1, 1, 1, max_download)

        video_lab = wx.StaticText(self.scrolled_panel, -1, "默认下载清晰度")
        self.video_quality_choice = wx.Choice(self.scrolled_panel, -1, choices = list(video_quality_mapping.keys()))
        self.video_quality_tip = wx.StaticBitmap(self.scrolled_panel, -1, wx.ArtProvider().GetBitmap(wx.ART_INFORMATION, size = self.FromDIP((16, 16))))
        self.video_quality_tip.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        video_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_hbox.Add(video_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        video_quality_hbox.Add(self.video_quality_choice, 0, wx.ALL, 10)
        video_quality_hbox.Add(self.video_quality_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        audio_lab = wx.StaticText(self.scrolled_panel, -1, "默认下载音质")
        self.audio_quality_choice = wx.Choice(self.scrolled_panel, -1, choices = list(audio_quality_mapping.keys()))
        self.audio_quality_tip = wx.StaticBitmap(self.scrolled_panel, -1, wx.ArtProvider().GetBitmap(wx.ART_INFORMATION, size = self.FromDIP((16, 16))))
        self.audio_quality_tip.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        sound_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        sound_quality_hbox.Add(audio_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        sound_quality_hbox.Add(self.audio_quality_choice, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        sound_quality_hbox.Add(self.audio_quality_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        codec_lab = wx.StaticText(self.scrolled_panel, -1, "视频编码格式")
        self.codec_choice = wx.Choice(self.scrolled_panel, -1, choices = ["AVC/H.264", "HEVC/H.265", "AV1"])
        self.codec_tip = wx.StaticBitmap(self.scrolled_panel, -1, wx.ArtProvider().GetBitmap(wx.ART_INFORMATION, size = self.FromDIP((16, 16))))
        self.codec_tip.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        codec_hbox = wx.BoxSizer(wx.HORIZONTAL)
        codec_hbox.Add(codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        codec_hbox.Add(self.codec_choice, 0, wx.ALL, 10)
        codec_hbox.Add(self.codec_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.speed_limit_chk = wx.CheckBox(self.scrolled_panel, -1, "对单个下载任务进行限速")
        self.speed_limit_lab = wx.StaticText(self.scrolled_panel, -1, "最高")
        self.speed_limit_box = wx.TextCtrl(self.scrolled_panel, -1, size = self.FromDIP((50, 25)))
        self.speed_limit_unit_lab = wx.StaticText(self.scrolled_panel, -1, "MB/s")

        speed_limit_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_limit_hbox.AddSpacer(30)
        speed_limit_hbox.Add(self.speed_limit_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        speed_limit_hbox.Add(self.speed_limit_box, 0, wx.ALL & (~wx.LEFT), 10)
        speed_limit_hbox.Add(self.speed_limit_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.add_number_chk = wx.CheckBox(self.scrolled_panel, -1, "批量下载视频时自动添加序号")
        self.show_toast_chk = wx.CheckBox(self.scrolled_panel, -1, "下载完成后弹出通知")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(path_lab, 0, wx.ALL, 10)
        vbox.Add(path_hbox, 0, wx.EXPAND)
        vbox.Add(self.max_thread_lab, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.max_thread_slider, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.max_download_lab, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.max_download_slider, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(video_quality_hbox, 0, wx.EXPAND)
        vbox.Add(sound_quality_hbox, 0, wx.EXPAND)
        vbox.Add(codec_hbox, 0, wx.EXPAND)
        vbox.Add(self.speed_limit_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        vbox.Add(speed_limit_hbox, 0, wx.EXPAND)
        vbox.Add(self.add_number_chk, 0, wx.ALL, 10)
        vbox.Add(self.show_toast_chk, 0, wx.ALL, 10)

        self.scrolled_panel.sizer.Add(vbox, 0, wx.EXPAND)

        download_sbox = wx.StaticBoxSizer(self.download_box)
        download_sbox.Add(self.scrolled_panel, 0, wx.EXPAND)

        download_vbox = wx.BoxSizer(wx.VERTICAL)
        download_vbox.Add(download_sbox, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(download_vbox)

        self.layout_sizer()

    def Bind_EVT(self):
        self.path_box.Bind(wx.EVT_TEXT, self.onChangePath)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePath)

        self.max_thread_slider.Bind(wx.EVT_SLIDER, self.onThreadSlide)
        self.max_download_slider.Bind(wx.EVT_SLIDER, self.onDownloadSlide)

        self.speed_limit_chk.Bind(wx.EVT_CHECKBOX, self.onChangeSpeedLimit)

        self.video_quality_tip.Bind(wx.EVT_LEFT_DOWN, self.onVideoQualityTip)
        self.audio_quality_tip.Bind(wx.EVT_LEFT_DOWN, self.onAudioQualityTip)
        self.codec_tip.Bind(wx.EVT_LEFT_DOWN, self.onCodecTip)

    def init_data(self):
        self.path_box.SetValue(Config.Download.path)
        
        self.max_thread_lab.SetLabel("多线程数：{}".format(Config.Download.max_thread_count))
        self.max_thread_slider.SetValue(Config.Download.max_thread_count)

        self.max_download_lab.SetLabel("并行下载数：{}".format(Config.Download.max_download_count))
        self.max_download_slider.SetValue(Config.Download.max_download_count)
        
        self.video_quality_choice.SetSelection(list(video_quality_mapping.values()).index(Config.Download.video_quality_id))
        self.audio_quality_choice.SetSelection(list(audio_quality_mapping.values()).index(Config.Download.audio_quality_id))

        self.codec_choice.SetSelection(list(video_codec_mapping.values()).index(Config.Download.video_codec))

        self.speed_limit_chk.SetValue(Config.Download.speed_limit)
        self.add_number_chk.SetValue(Config.Download.add_number)
        self.show_toast_chk.SetValue(Config.Download.show_notification)

        self.speed_limit_box.SetValue(str(Config.Download.speed_limit_in_mb))

        self.onChangeSpeedLimit(0)

    def save(self):
        default_path = os.path.join(os.getcwd(), "download")

        Config.Download.path = self.path_box.GetValue()
        Config.Download.max_thread_count = self.max_thread_slider.GetValue()
        Config.Download.max_download_count = self.max_download_slider.GetValue()
        Config.Download.video_quality_id = video_quality_mapping[self.video_quality_choice.GetStringSelection()]
        Config.Download.audio_quality_id = audio_quality_mapping[self.audio_quality_choice.GetStringSelection()]
        Config.Download.video_codec = video_codec_mapping[self.codec_choice.GetStringSelection()]
        Config.Download.add_number = self.add_number_chk.GetValue()
        Config.Download.show_notification = self.show_toast_chk.GetValue()
        Config.Download.speed_limit = self.speed_limit_chk.GetValue()
        Config.Download.speed_limit_in_mb = int(self.speed_limit_box.GetValue())

        conf.config.set("download", "path", Config.Download.path if self.path_box.GetValue() != default_path else "")
        conf.config.set("download", "max_thread", str(Config.Download.max_thread_count))
        conf.config.set("download", "max_download", str(Config.Download.max_download_count))
        conf.config.set("download", "video_quality", str(Config.Download.video_quality_id))
        conf.config.set("download", "audio_quality", str(Config.Download.audio_quality_id))
        conf.config.set("download", "video_codec", Config.Download.video_codec)
        conf.config.set("download", "add_number", str(int(Config.Download.add_number)))
        conf.config.set("download", "show_notification", str(int(Config.Download.show_notification)))
        conf.config.set("download", "speed_limit", str(int(Config.Download.speed_limit)))
        conf.config.set("download", "speed_limit_in_mb", str(Config.Download.speed_limit_in_mb))

        conf.config_save()

        # 更新下载窗口中并行下载数信息
        self.GetParent().GetParent().GetParent().download_window.update_max_download_choice()

    def onConfirm(self):
        if not self.isValidSpeedLimit(self.speed_limit_box.GetValue()):
            wx.MessageDialog(self, "速度值无效\n\n输入的速度值无效，应为一个正整数", "警告", wx.ICON_WARNING).ShowModal()
            return False
        
        self.save()

        return True
    
    def onBrowsePath(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = Config.Download.path)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()
            self.path_box.SetValue(save_path)

        dlg.Destroy()

    def onChangePath(self, event):
        self.path_box.SetToolTip(self.path_box.GetValue())

    def onThreadSlide(self, event):
        self.max_thread_lab.SetLabel("多线程数：{}".format(self.max_thread_slider.GetValue()))

    def onDownloadSlide(self, event):
        self.max_download_lab.SetLabel("并行下载数：{}".format(self.max_download_slider.GetValue()))

    def onChangeSpeedLimit(self, event):
        if self.speed_limit_chk.GetValue():
            self.speed_limit_box.Enable(True)

            self.speed_limit_lab.Enable(True)
            self.speed_limit_unit_lab.Enable(True)
        else:
            self.speed_limit_box.Enable(False)

            self.speed_limit_lab.Enable(False)
            self.speed_limit_unit_lab.Enable(False)

    def isValidSpeedLimit(self, speed):
        return bool(re.fullmatch(r'[1-9]\d*', speed))
    
    def onVideoQualityTip(self, event):
        wx.MessageDialog(self, "默认下载清晰度选项说明\n\n指定下载视频的清晰度，取决于视频的支持情况；若视频无所选的清晰度，则自动下载最高可用的清晰度\n\n自动：自动下载每个视频的最高可用的清晰度", "说明", wx.ICON_INFORMATION).ShowModal()

    def onAudioQualityTip(self, event):
        wx.MessageDialog(self, "默认下载音质选项说明\n\n指定下载视频的音质，取决于视频的支持情况；若视频无所选的音质，则自动下载最高可用的音质\n\n自动：自动下载每个视频的最高可用音质", "说明", wx.ICON_INFORMATION).ShowModal()

    def onCodecTip(self, event):
        wx.MessageDialog(self, "视频编码格式选项说明\n\n指定下载视频的编码格式，取决于视频的支持情况；若视频无所选的编码格式，则自动下载 H.264", "说明", wx.ICON_INFORMATION).ShowModal()

    def layout_sizer(self):
        self.scrolled_panel.Layout()

        self.scrolled_panel.sizer.Layout()

        self.scrolled_panel.SetupScrolling(scroll_x = False, scrollToTop = False)

    def getPanelSize(self):
        match Config.Sys.platform:
            case "windows":
                return self.FromDIP((-1, 350))
            
            case "linux" | "darwin":
                return self.FromDIP((400, 430))

class MergeTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        ffmpeg_box = wx.StaticBox(self, -1, "FFmpeg 设置")

        ffmpeg_path_label = wx.StaticText(ffmpeg_box, -1, "FFmpeg 路径")
        self.path_box = wx.TextCtrl(ffmpeg_box, -1, size = self.FromDIP((220, 24)))
        self.browse_btn = wx.Button(ffmpeg_box, -1, "浏览", size = self.FromDIP((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        self.auto_detect_btn = wx.Button(ffmpeg_box, -1, "自动检测", size = self.FromDIP((90, 28)))
        self.tutorial_btn = wx.Button(ffmpeg_box, -1, "安装教程", size = self.FromDIP((90, 28)))

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.Add(self.auto_detect_btn, 0, wx.ALL & (~wx.TOP), 10)
        btn_hbox.Add(self.tutorial_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        ffmpeg_vbox = wx.BoxSizer(wx.VERTICAL)
        ffmpeg_vbox.Add(ffmpeg_path_label, 0, wx.ALL, 10)
        ffmpeg_vbox.Add(path_hbox, 0, wx.EXPAND)
        ffmpeg_vbox.Add(btn_hbox, 0, wx.EXPAND)

        ffmpeg_sbox = wx.StaticBoxSizer(ffmpeg_box)
        ffmpeg_sbox.Add(ffmpeg_vbox, 1, wx.EXPAND)

        merge_option_box = wx.StaticBox(self, -1, "合成选项")

        self.auto_clean_chk = wx.CheckBox(merge_option_box, -1, "合成完成后清理文件")

        merge_option_vbox = wx.BoxSizer(wx.VERTICAL)
        merge_option_vbox.Add(self.auto_clean_chk, 0, wx.ALL, 10)

        merge_option_sbox = wx.StaticBoxSizer(merge_option_box)
        merge_option_sbox.Add(merge_option_vbox, 0, wx.EXPAND)

        merge_vbox = wx.BoxSizer(wx.VERTICAL)
        merge_vbox.Add(ffmpeg_sbox, 0, wx.ALL | wx.EXPAND, 10)
        merge_vbox.Add(merge_option_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, 10)

        self.SetSizer(merge_vbox)
    
    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePath)

        self.auto_detect_btn.Bind(wx.EVT_BUTTON, self.onAutoDetect)

        self.tutorial_btn.Bind(wx.EVT_BUTTON, self.onTutorial)

    def init_data(self):
        self.path_box.SetValue(Config.FFmpeg.path)
        
        self.auto_clean_chk.SetValue(Config.Merge.auto_clean)

    def save(self):
        Config.FFmpeg.path = self.path_box.GetValue()
        Config.Merge.auto_clean = self.auto_clean_chk.GetValue()

        conf.config.set("merge", "ffmpeg_path", Config.FFmpeg.path)
        conf.config.set("merge", "auto_clean", str(int(Config.Merge.auto_clean)))

    def onBrowsePath(self, event):
        default_dir = os.path.dirname(self.path_box.GetValue())

        # 根据不同平台选取不同后缀名文件
        match Config.Sys.platform:
            case "windows":
                defaultFile = "ffmpeg.exe"
                wildcard = ("FFmpeg|ffmpeg.exe")

            case "linux" | "darwin":
                defaultFile = "ffmpeg"
                wildcard = ("FFmpeg|ffmpeg")

        dlg = wx.FileDialog(self, "选择 FFmpeg 路径", defaultDir = default_dir, defaultFile = defaultFile, style = wx.FD_OPEN, wildcard = wildcard)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()
            self.path_box.SetValue(save_path)

        dlg.Destroy()

    def onAutoDetect(self, event):
        detect_window = DetectDialog(self)

        if detect_window.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(detect_window.getPath())

    def onTutorial(self, event):
        import webbrowser

        webbrowser.open("https://scott-sloan.cn/archives/120/")

    def onConfirm(self):
        self.save()

        return True
    
class ProxyTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        proxy_box = wx.StaticBox(self, -1, "代理设置")

        proxy_tip = wx.StaticText(proxy_box, -1, "代理选项")
        
        self.proxy_disable_radio = wx.RadioButton(proxy_box, -1, "不使用代理")
        self.proxy_follow_radio = wx.RadioButton(proxy_box, -1, "跟随系统")
        self.proxy_manual_radio = wx.RadioButton(proxy_box, -1, "手动设置")

        proxy_hbox = wx.BoxSizer(wx.HORIZONTAL)
        proxy_hbox.Add(self.proxy_disable_radio, 0, wx.ALL, 10)
        proxy_hbox.Add(self.proxy_follow_radio, 0, wx.ALL, 10)
        proxy_hbox.Add(self.proxy_manual_radio, 0, wx.ALL, 10)
        
        ip_lab = wx.StaticText(proxy_box, -1, "地址")
        self.ip_box = wx.TextCtrl(proxy_box, -1, size = self.FromDIP((150, 25)))

        port_lab = wx.StaticText(proxy_box, -1, "端口")
        self.port_box = wx.TextCtrl(proxy_box, -1, size = self.FromDIP((75, 25)))

        self.auth_chk = wx.CheckBox(proxy_box, -1, "启用代理身份验证")
        
        uname_lab = wx.StaticText(proxy_box, -1, "用户名")
        self.uname_box = wx.TextCtrl(proxy_box, -1, size = self.FromDIP((150, 25)))

        pwd_lab = wx.StaticText(proxy_box, -1, "密码")
        self.passwd_box = wx.TextCtrl(proxy_box, -1, size = self.FromDIP((150, 25)))

        self.test_btn = wx.Button(proxy_box, -1, "测试", size = self.FromDIP((80, 30)))

        bag_box = wx.GridBagSizer(5, 4)
        bag_box.Add(ip_lab, pos = (0, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.ip_box, pos = (0, 1), span = (1, 3), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = 10)
        bag_box.Add(port_lab, pos = (1, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.port_box, pos = (1, 1), span = (1, 2), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = 10)
        bag_box.Add(self.auth_chk, pos = (2, 0), span = (1, 2), flag = wx.ALL | wx.EXPAND, border = 10)
        bag_box.Add(uname_lab, pos = (3, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.uname_box, pos = (3, 1), span = (1, 3), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = 10)
        bag_box.Add(pwd_lab, pos = (4, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.passwd_box, pos = (4, 1), span = (1, 3), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(proxy_tip, 0, wx.ALL & (~wx.BOTTOM), 10)
        vbox.Add(proxy_hbox, 0, wx.EXPAND)
        vbox.Add(bag_box)
        vbox.Add(self.test_btn, 0, wx.ALL, 10)

        proxy_sbox = wx.StaticBoxSizer(proxy_box)
        proxy_sbox.Add(vbox, 0, wx.EXPAND)

        proxy_vbox = wx.BoxSizer(wx.VERTICAL)
        proxy_vbox.Add(proxy_sbox, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(proxy_vbox)
    
    def Bind_EVT(self):
        self.proxy_disable_radio.Bind(wx.EVT_RADIOBUTTON, self.onProxyRadioEVT)
        self.proxy_follow_radio.Bind(wx.EVT_RADIOBUTTON, self.onProxyRadioEVT)
        self.proxy_manual_radio.Bind(wx.EVT_RADIOBUTTON, self.onProxyRadioEVT)

        self.auth_chk.Bind(wx.EVT_CHECKBOX, self.onAuthCheckEVT)
        
        self.test_btn.Bind(wx.EVT_BUTTON, self.onTestEVT)

    def init_data(self):
        match Config.Proxy.proxy_mode:
            case Config.Type.PROXY_DISABLE:
                self.proxy_disable_radio.SetValue(True)

                self.setProxyEnable(False)

            case Config.Type.PROXY_FOLLOW:
                self.proxy_follow_radio.SetValue(True)

                self.setProxyEnable(False)

            case Config.Type.PROXY_MANUAL:
                self.proxy_manual_radio.SetValue(True)

                self.setProxyEnable(True)

        if not Config.Proxy.auth_enable:
            self.setAuthEnable(False)

        self.ip_box.SetValue(Config.Proxy.proxy_ip_addr)
        self.port_box.SetValue(Config.Proxy.proxy_port)
    
        self.auth_chk.SetValue(Config.Proxy.auth_enable)
        self.uname_box.SetValue(Config.Proxy.auth_uname)
        self.passwd_box.SetValue(Config.Proxy.auth_passwd)

    def save(self):
        if self.proxy_disable_radio.GetValue():
            proxy = Config.Type.PROXY_DISABLE

        elif self.proxy_follow_radio.GetValue():
            proxy = Config.Type.PROXY_FOLLOW

        else:
            proxy = Config.Type.PROXY_MANUAL

        Config.Proxy.proxy_mode = proxy

        Config.Proxy.proxy_ip_addr = self.ip_box.GetValue()
        Config.Proxy.proxy_port = self.port_box.GetValue()

        Config.Proxy.auth_enable = self.auth_chk.GetValue()
        Config.Proxy.auth_uname = self.uname_box.GetValue()
        Config.Proxy.auth_passwd = self.passwd_box.GetValue()

        conf.config.set("proxy", "proxy_mode", str(Config.Proxy.proxy_mode))
        conf.config.set("proxy", "ip_addr", Config.Proxy.proxy_ip_addr)
        conf.config.set("proxy", "port", Config.Proxy.proxy_port)

        conf.config.set("proxy", "auth_enable", str(int(Config.Proxy.auth_enable)))
        conf.config.set("proxy", "uname", Config.Proxy.auth_uname)
        conf.config.set("proxy", "passwd", Config.Proxy.auth_passwd)

        conf.config_save()

    def setProxyEnable(self, enable):
        self.ip_box.Enable(enable)
        self.port_box.Enable(enable)

    def setAuthEnable(self, enable):
        self.uname_box.Enable(enable)
        self.passwd_box.Enable(enable)

    def onProxyRadioEVT(self, event):
        if self.proxy_disable_radio.GetValue():
            self.setProxyEnable(False)

        elif self.proxy_follow_radio.GetValue():
            self.setProxyEnable(False)

        else:
            self.setProxyEnable(True)

    def onAuthCheckEVT(self, event):
        if event.IsChecked():
            self.setAuthEnable(True)
        else:
            self.setAuthEnable(False)
 
    def onTestEVT(self, event):
        if self.proxy_manual_radio.GetValue():
            proxy = {
                "http": f"{self.ip_box.GetValue()}:{self.port_box.GetValue()}",
                "https": f"{self.ip_box.GetValue()}:{self.port_box.GetValue()}"
            }
        else:
            proxy = {}

        if self.auth_chk.GetValue():
            auth = HTTPProxyAuth(
                self.uname_box.GetValue(),
                self.passwd_box.GetValue()
            )
        else:
            auth = HTTPProxyAuth(None, None)

        Thread(target = self.testProxy, args = (proxy, auth, )).start()

    def testProxy(self, proxy, auth):
        try:
            start_time = time.time()

            url = "https://www.bilibili.com"
            req = requests.get(url, headers = get_header(), proxies = proxy, auth = auth, timeout = 5)
            
            end_time = time.time()

            wx.MessageDialog(self, f"测试成功\n\n请求站点：{url}\n状态码：{req.status_code}\n耗时：{round(end_time - start_time, 1)}s", "提示", wx.ICON_INFORMATION).ShowModal()

        except requests.RequestException as e:
            wx.MessageDialog(self, f"测试失败\n\n请求站点：{url}\n错误信息：\n\n{e}", "测试代理", wx.ICON_WARNING).ShowModal()

    def onConfirm(self):
        self.save()

        return True

class MiscTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        sections_box = wx.StaticBox(self, -1, "剧集列表显示设置")

        self.episodes_single_choice = wx.RadioButton(sections_box, -1, "仅获取单个视频")
        self.episodes_in_section_choice = wx.RadioButton(sections_box, -1, "获取视频所在合集")
        self.episodes_all_sections_choice = wx.RadioButton(sections_box, -1, "获取全部相关视频 (包括花絮、PV、OP、ED 等)")

        self.show_episode_full_name = wx.CheckBox(sections_box, -1, "显示完整剧集名称")
        self.auto_select_chk = wx.CheckBox(sections_box, -1, "自动勾选全部视频")

        sections_vbox = wx.BoxSizer(wx.VERTICAL)
        sections_vbox.Add(self.episodes_single_choice, 0, wx.ALL, 10)
        sections_vbox.Add(self.episodes_in_section_choice, 0, wx.ALL & (~wx.TOP), 10)
        sections_vbox.Add(self.episodes_all_sections_choice, 0, wx.ALL & (~wx.TOP), 10)
        sections_vbox.Add(self.show_episode_full_name, 0, wx.ALL & (~wx.BOTTOM), 10)
        sections_vbox.Add(self.auto_select_chk, 0, wx.ALL, 10)
        
        sections_sbox = wx.StaticBoxSizer(sections_box)
        sections_sbox.Add(sections_vbox, 0, wx.EXPAND)

        player_box = wx.StaticBox(self, -1, "播放器设置")

        path_lab = wx.StaticText(player_box, -1, "播放器路径")
        self.path_box = wx.TextCtrl(player_box, -1, size = self.FromDIP((220, 24)))
        self.browse_btn = wx.Button(player_box, -1, "浏览")

        player_hbox = wx.BoxSizer(wx.HORIZONTAL)
        player_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        player_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        
        player_vbox = wx.BoxSizer(wx.VERTICAL)
        player_vbox.Add(path_lab, 0, wx.ALL, 10)
        player_vbox.Add(player_hbox, 1, wx.EXPAND)

        player_sbox = wx.StaticBoxSizer(player_box)
        player_sbox.Add(player_vbox, 1, wx.EXPAND)

        misc_box = wx.StaticBox(self, -1, "杂项")
        self.check_update_chk = wx.CheckBox(misc_box, -1, "自动检查更新")
        self.debug_chk = wx.CheckBox(misc_box, -1, "启用调试模式")

        misc_vbox = wx.BoxSizer(wx.VERTICAL)
        misc_vbox.Add(self.check_update_chk, 0, wx.ALL, 10)
        misc_vbox.Add(self.debug_chk, 0, wx.ALL & ~(wx.TOP), 10)

        misc_sbox = wx.StaticBoxSizer(misc_box)
        misc_sbox.Add(misc_vbox, 0, wx.EXPAND)

        misc_vbox = wx.BoxSizer(wx.VERTICAL)
        misc_vbox.Add(sections_sbox, 0, wx.ALL | wx.EXPAND, 10)
        misc_vbox.Add(player_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, 10)
        misc_vbox.Add(misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, 10)

        self.SetSizer(misc_vbox)

    def Bind_EVT(self):
        self.path_box.Bind(wx.EVT_TEXT, self.onChangePath)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.browse_btn_EVT)

    def init_data(self):
        match Config.Misc.episode_display_mode:
            case 0:
                self.episodes_single_choice.SetValue(True)

            case 1:
                self.episodes_in_section_choice.SetValue(True)
                
            case 2:
                self.episodes_all_sections_choice.SetValue(True)

        self.show_episode_full_name.SetValue(Config.Misc.show_episode_full_name)
        self.auto_select_chk.SetValue(Config.Misc.auto_select)
        self.path_box.SetValue(Config.Misc.player_path)
        self.check_update_chk.SetValue(Config.Misc.check_update)
        self.debug_chk.SetValue(Config.Misc.debug)

    def save(self):
        if self.episodes_single_choice.GetValue():
            Config.Misc.episode_display_mode = Config.Type.EPISODES_SINGLE

        elif self.episodes_in_section_choice.GetValue():
            Config.Misc.episode_display_mode = Config.Type.EPISODES_IN_SECTION

        elif self.episodes_all_sections_choice.GetValue():
            Config.Misc.episode_display_mode = Config.Type.EPISODES_ALL_SECTIONS

        Config.Misc.auto_select = self.auto_select_chk.GetValue()
        Config.Misc.player_path = self.path_box.GetValue()
        Config.Misc.check_update = self.check_update_chk.GetValue()
        Config.Misc.debug = self.debug_chk.GetValue()

        conf.config.set("misc", "auto_select", str(int(Config.Misc.auto_select)))
        conf.config.set("misc", "show_episode_full_name", str(int(Config.Misc.show_episode_full_name)))
        conf.config.set("misc", "episode_display_mode", str(int(Config.Misc.episode_display_mode)))
        conf.config.set("misc", "player_path", Config.Misc.player_path)
        conf.config.set("misc", "check_update", str(int(Config.Misc.check_update)))
        conf.config.set("misc", "debug", str(int(Config.Misc.debug)))

        conf.config_save()

        # 重新创建主窗口的菜单
        self.GetParent().GetParent().GetParent().init_menubar()

    def browse_btn_EVT(self, event):
        wildcard = "可执行文件(*.exe)|*.exe"
        dialog = wx.FileDialog(self, "选择播放器路径", os.getcwd(), wildcard = wildcard, style = wx.FD_OPEN)

        if dialog.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dialog.GetPath())

    def onChangePath(self, event):
        self.path_box.SetToolTip(self.path_box.GetValue())
    
    def onConfirm(self):
        self.save()

        return True