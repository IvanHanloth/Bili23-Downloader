# Bili23-Downloader
![](https://img.shields.io/badge/Latest_Version-1.13-green.svg) ![](https://img.shields.io/badge/Python-3.8.10-green.svg) ![](https://img.shields.io/badge/wxPython-4.1.1-green.svg)  
  
下载 Bilibili 视频/番剧/电影/纪录片 等资源  
## 声明
#### 本程序仅供学习交流使用，请勿用于商业用途。  
## 功能介绍
- **支持输入的 URL 链接**
> - 用户投稿类型视频链接
> - 剧集（番剧，电影，纪录片等）链接
> - b23.tv 短链接
> - 部分视频可直接输入编号：
> > - 视频 av 或 BV 号
> > - 剧集 epid 或 md（media_id） 或 ss（season_id） 号
- **支持 GUI 图形界面**  
> - 显示剧集列表，可勾选需要下载的部分
> - 显示视频相关信息（封面，播放数，三连数等）
- **支持下载弹幕和字幕**  
> - 弹幕目前仅支持下载 xml 格式，后续会支持 ass，proto 等格式
> - 字幕可保存为 srt 格式 (测试中)
> - 可自动合成字幕 (测试中)
- **支持自定义清晰度下载**  
> - 可自定义清晰度（取决于视频所支持的清晰度）  
> - 免登录下载 `1080P` 视频  
> - **注：`1080P+` 及以上清晰度需要使用大会员 Cookie 才能下载。**
## 安装
- **安装程序所需依赖**
```
pip install -r requirements.txt
```
## 运行截图
> - 主界面
> > - ![主界面](https://github.com/ScottSloan/Bili23-Downloader/blob/main/assets/main.png)
> - 查看番剧信息
> > - ![查看番剧信息](https://github.com/ScottSloan/Bili23-Downloader/blob/main/assets/info.png)
> - 下载完成
> > - ![下载完成](https://github.com/ScottSloan/Bili23-Downloader/blob/main/assets/play.png)
## 使用 Cookie
- **适用于需要使用大会员 Cookie 才能下载的情况**
> - 浏览器登录B站，按下 `F12` 键打开开发者模式--> application --> cookie，找到 SESSDATA 字段，在设置中粘贴即可
> - **注：Cookie 有效期为一个月，请定期更换。**
## 开发日志
- **[最新] 版本 1.13 (2022-3-13)**
> - 番组现已支持 番剧/电影/纪录片/综艺/国创/电视剧 类型的下载
> - 现在合集视频能够显示完整列表
> - 添加了"设置"功能
> - 优化了部分细节效果
> - 修正了部分已知问题
- **版本 1.12 (2022-2-20)**
> - 程序初始版本发布
> - 可下载B站的视频和番剧，方便离线观看
