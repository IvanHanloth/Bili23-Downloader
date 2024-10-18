import re
import json
import requests
from typing import List, Dict

from utils.config import Config, Audio
from utils.tools import get_header, get_auth, get_proxy, convert_to_bvid, find_str
from utils.error import process_exception, ParseError, ErrorUtils, URLError, StatusCode

class MusicInfo:
    url: str = ""
    sid: int = 0 #音乐id
    slid: int = 0 #音乐列表id
    quality: str = ""
    privilege: int = 2
    mid: int = 0 #可为任意值
    platform: str = "android"

    title: str = ""
    cover: str = ""
    type: int = 0

    music_list: List = []
    music_quality_id_list: List = []
    music_quality_desc_list: List = []

    sections: Dict = {}

class MusicParser:
    def __init__(self):
        pass
    
    @process_exception
    def get_slid(self, url: str):
        #获取slid
        slid = re.findall(r"am([0-9]+)",url)

        if not slid:
            raise URLError()
        
        MusicInfo.slid=slid
        
    @process_exception
    def get_songid(self, url: str):
        #获取sid
        sid = re.findall(r"au([0-9]+)", url)

        if not sid:
            raise URLError()
        
        MusicInfo.sid=sid

    @process_exception
    def get_all_song(self):
        #获取所有音乐
        url = f"https://www.bilibili.com/audio/music-service-c/web/song/of-menu?sid={MusicInfo.slid}&pn=1&ps=100"#暂时不考虑超过一页的音乐

        req = requests.get(url, headers = get_header(referer_url = MusicInfo.url), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)
        data=resp["data"]
        if not data:
            raise URLError()
        
        if "data" not in data:
            raise URLError()
        
        music_list = data["data"]

        MusicInfo.music_list = music_list


    @process_exception
    def get_video_info(self):
        # 获取音频信息
        url = f"https://www.bilibili.com/audio/music-service-c/web/song/info?sid={MusicInfo.sid}"
        
        req = requests.get(url, headers = get_header(referer_url = MusicInfo.url, cookie = Config.User.sessdata), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        MusicInfo.title = info["title"]
        MusicInfo.cover = info["cover"]
        MusicInfo.quality = info["quality"]

        ## TODO 由于音乐接口返回的音频无法下载，此行以下暂时不处理

        # 当解析单个视频时，取 pages 中的 cid，使得清晰度和音质识别更加准确
        if Config.Misc.episode_display_mode == Config.Type.EPISODES_SINGLE:
            if hasattr(self, "part_num"):
                MusicInfo.cid = MusicInfo.pages_list[self.part_num - 1]["cid"]
            else:
                MusicInfo.cid = info["pages"][0]["cid"]
        else:
            MusicInfo.cid = info["cid"]

        match Config.Misc.episode_display_mode:
            case Config.Type.EPISODES_SINGLE:
                # 解析单个视频

                self.parse_pages()

            case Config.Type.EPISODES_IN_SECTION:
                # 解析视频所在合集

                if "ugc_season" in info:
                    # 判断是否为合集视频，若是则设置类型为合集
                    MusicInfo.type = Config.Type.VIDEO_TYPE_SECTIONS

                    info_section = info["ugc_season"]["sections"]

                    for section_entry in info_section:
                        section_title = section_entry["title"]
                        info_episodes = section_entry["episodes"]

                        for episode_entry in info_episodes:
                            if episode_entry["bvid"] == MusicInfo.bvid:
                                # 解析此部分内容
                                for index, value in enumerate(info_episodes):
                                    value["title"] = str(index + 1)
                                    break

                                MusicInfo.sections[section_title] = info_episodes
                else:
                    # 非合集视频，判断是否为分P视频
                    self.parse_pages()

            case Config.Type.EPISODES_ALL_SECTIONS:
                # 解析全部相关视频
    
                if "ugc_season" in info:
                    # 判断是否为合集视频，若是则设置类型为合集
                    MusicInfo.type = Config.Type.VIDEO_TYPE_SECTIONS

                    info_ugc_season = info["ugc_season"]
                    info_section = info_ugc_season["sections"]
                    
                    MusicInfo.title = info_ugc_season["title"]
                    
                    for section in info_section:
                        section_title = section["title"]
                        section_episodes = section["episodes"]

                        for index, value in enumerate(section_episodes):
                            value["title"] = str(index + 1)

                            MusicInfo.sections[section_title] = section_episodes
                else:
                    # 非合集视频，判断是否为分P视频
                    self.parse_pages()

    @process_exception
    def get_video_available_media_info(self):
        # 获取视频清晰度
        url = f"https://api.bilibili.com/x/player/playurl?bvid={MusicInfo.bvid}&cid={MusicInfo.cid}&qn=0&fnver=0&fnval=4048&fourk=1"
                
        req = requests.get(url, headers = get_header(referer_url = MusicInfo.url, cookie = Config.User.sessdata), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        MusicInfo.video_quality_id_list = info["accept_quality"]
        MusicInfo.video_quality_desc_list = info["accept_description"]

        # 检测无损或杜比是否存在
        if "flac" in info["dash"]:
            if info["dash"]["flac"]:
                Audio.q_hires = True

        if "dolby" in info["dash"]:
            if info["dash"]["dolby"]["audio"]:
                Audio.q_dolby = True

        # 检测 192k, 132k, 64k 音质是否存在
        if "audio" in info["dash"]:
            if info["dash"]["audio"]:
                for entry in info["dash"]["audio"]:
                    match entry["id"]:
                        case 30280:
                            Audio.q_192k = True

                        case 30232:
                            Audio.q_132k = True

                        case 30216:
                            Audio.q_64k = True

            Audio.audio_quality_id = Config.Download.audio_quality_id

    def parse_url(self, url: str):
        # 先检查是否为分 P 视频
        self.get_part(url)

        # 清除当前的视频信息
        self.clear_video_info()

        match find_str(r"av|BV", url):
            case "av":
                self.get_aid(url)

            case "BV":
                self.get_bvid(url)

        self.get_video_info()

        self.get_video_available_media_info()

    def set_bvid(self, bvid: str):
        MusicInfo.bvid, MusicInfo.url = bvid, f"https://www.bilibili.com/video/{bvid}"

    def check_json(self, json: Dict):
        # 检查接口返回状态码
        status_code = json["code"]
        error = ErrorUtils()

        if status_code != StatusCode.CODE_0:
            # 如果请求失败，则抛出 ParseError 异常，由 process_exception 进一步处理
            raise ParseError(error.getStatusInfo(status_code), status_code)

    def parse_pages(self):
        # 判断是否为分P视频
        if len(MusicInfo.pages_list) == 1:
            # 单个视频
            MusicInfo.type = Config.Type.VIDEO_TYPE_SINGLE
        else:
            # 分P视频
            MusicInfo.type = Config.Type.VIDEO_TYPE_PAGES

            if hasattr(self, "part_num"):
                MusicInfo.pages_list = [MusicInfo.pages_list[self.part_num - 1]]
            else:
                MusicInfo.pages_list = [MusicInfo.pages_list[0]]

    def clear_video_info(self):
        # 清除当前的视频信息
        MusicInfo.url = MusicInfo.aid = MusicInfo.bvid = MusicInfo.title = MusicInfo.cover = ""
        MusicInfo.cid = MusicInfo.type = 0

        MusicInfo.pages_list.clear()
        MusicInfo.episodes_list.clear()
        MusicInfo.video_quality_id_list.clear()
        MusicInfo.video_quality_desc_list.clear()

        MusicInfo.sections.clear()

        # 重置音质信息
        Audio.q_hires = Audio.q_dolby = Audio.q_192k = Audio.q_132k = Audio.q_64k = Audio.audio_only = False
        Audio.audio_quality_id = 0