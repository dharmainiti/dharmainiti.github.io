#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author: Minions
# @Date: 2021-04-28 10:59:25
# @Last Modified by:  Minions
# @Last Modified time: 2021-04-28 21:15:36

import requests
from lxml import etree
import re
import json
import time
import xmltodict

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36"
}


class Bili(object):
    def __init__(self, keyword):
        self.film_id = self.get_film_id(keyword)
        if self.film_id is None:
            exit()
        self.film_oid, self.film_cid = self.get_film_oid_cid()
        self.first_level_rpids = [] # 存储一级评论的rpid,方便抓取回复的评论


    def get_film_id(self, keyword):
        """
            func: 获取搜索电影的详情页面的id,可用于查找评论所需的oid

            args
                keyword: 搜索关键字(目前只能输入电影名称)

            return: str:film_id
        """
        search_url = "https://search.bilibili.com/all?keyword=" + keyword
        resp = requests.get(search_url, headers=HEADERS)
        html = etree.HTML(resp.text)
        search_film_detail_url = html.xpath("//div["
                                            "@class='pgc-item-wrap']/a/@href")
        # print(film_detail_url)
        # 如果匹配不成功,即找不到该电影len(film_detail_url)=0
        if len(search_film_detail_url):
            file_id = re.findall('\d+', search_film_detail_url[0])[0]
            return file_id
        else:
            print("！请检查输入的电影名称！")


    def get_film_oid_cid(self):
        """
            func: 获取电影的oid和cid,oid在评论中用到，cid在弹幕中用到

            return: str:film_oid str:film_cid
        """
        film_detail_url = "https://www.bilibili.com/bangumi/play/ss" + \
                       self.film_id + "/?from=search"
        resp = requests.get(film_detail_url, headers=HEADERS)
        # print(resp.text)
        aid = re.findall('"episodes":\[\{"aid":(\d+),', resp.text)[0]
        film_cid = re.findall('"cid":(\d+),"cover"', resp.text)[0]
        film_oid = aid
        return film_oid, film_cid


    def get_film_detail_info(self):
        """
            func: 获取电影的详情信息(如投币数,弹幕数...)

            return: 返回电影详情信息
        """
        film_detail_url = "https://www.bilibili.com/bangumi/play/ss" + \
                          self.film_id + "/?from=search"

        resp = requests.get(film_detail_url, headers=HEADERS)
        json_text = re.findall('__INITIAL_STATE__=(.*?),"sponsor"',
                               resp.text)[0] + '}'
        print(json_text)
        film_info_dict = json.loads(json_text)
        mediaInfo = film_info_dict["mediaInfo"]
        cover = mediaInfo["cover"]  # 视频封面
        evaluate = mediaInfo["evaluate"]  # 视频简介
        desc = mediaInfo["new_ep"]["desc"]  # 上映时间
        pub_time = mediaInfo["publish"]["pub_time"]  # 上映到b站时间
        score = mediaInfo["rating"]["score"]  # 评分
        count = mediaInfo["rating"]["count"]  # 评分人的个数
        coins = mediaInfo["stat"]["coins"]  # 投币次数
        danmakus = mediaInfo["stat"]["danmakus"]  # 弹幕总数
        favorites = mediaInfo["stat"]["favorites"]  # 追剧总数
        share = mediaInfo["stat"]["share"]  # 分享总数
        views = mediaInfo["stat"]["views"]  # 观看总数(播放量)
        aid = mediaInfo["episodes"][0]["aid"]  # aid=oid在评论和许多地方要用到
        cid = mediaInfo["episodes"][0]["cid"]  # cid用于弹幕抓取
        print(cover, evaluate, desc, pub_time, score, count, coins, danmakus,
              favorites, share, views, aid, cid)


    def get_first_level_comments(self):
        """
            func: 获取电影下面的一级评论以及评论有关信息

            return: 返回一级评论的详情信息
        """
        for i in range(1, 10):
            print("-" * 30 + str(i) + "-" * 30)
            comment_url = "https://api.bilibili.com/x/v2/reply/main?&next" \
                          "=%d&type=1&oid="%i + self.film_oid
            resp = requests.get(comment_url, headers=HEADERS)
            comments_json_text = json.loads(resp.text)
            replies = comments_json_text["data"]["replies"]
            for reply in replies:
                message = reply["content"]["message"]   # 评论内容
                rcount = reply["rcount"]    # 评论回复人数
                like = reply["like"]    # 评论点赞人数
                ctime = reply["ctime"]    # 评论时间戳
                mid = reply["member"]["mid"]    # 评论用户的ID
                current_level = reply["member"]["level_info"]["current_level"]  #
                #  用户等级
                root = reply["rpid"]    # 二级评论及以下需要父集的rpid
                self.first_level_rpids.append(root)
                # print(message)
                # print(message, rcount, like, ctime, mid, current_level)

            time.sleep(2.0)


    def get_not_first_level_comments(self):
        """
            func: 获取电影下面的非一级评论以及评论有关信息

        """
        # 获取非一级评论需先把一级评论下的rpid拿到
        self.get_first_level_comments()
        for rpid in self.first_level_rpids:
            print("-"*30 + "当前rpid为%s"%rpid + "-"*30)
            for i in range(1, 15):
                print("-" * 30 + "第%s页"%str(i) + "-" * 30)
                comment_url = "https://api.bilibili.com/x/v2/reply/reply?&pn=" \
                              + str(i) +"&type=1&oid="+ str(self.film_oid) \
                              +"&root=" + str(rpid)
                # print(comment_url)
                resp = requests.get(comment_url, headers=HEADERS)
                comments_json_text = json.loads(resp.text)
                replies = comments_json_text["data"]["replies"]

                if replies is None:
                    print("该评论回复只有%d页"%(i-1))
                    break

                for reply in replies:
                    message = reply["content"]["message"]  # 评论内容
                    rcount = reply["rcount"]  # 评论回复人数
                    like = reply["like"]  # 评论点赞人数
                    ctime = reply["ctime"]  # 评论时间戳
                    mid = reply["member"]["mid"]  # 评论用户的ID
                    current_level = reply["member"]["level_info"][
                        "current_level"]  # 用户等级

                    # 去掉回复xxx:
                    try:
                        message = re.findall(":(.*)", message)[0]
                    except:
                        pass
                    print(message)

                time.sleep(1.0)


    def get_bullet_chat(self):
        """
            func: 获取弹幕内容

        """
        bullet_chat_url = "https://api.bilibili.com/x/v1/dm/list.so?oid=" + \
                          str(self.film_cid)
        resp = requests.get(bullet_chat_url, headers=HEADERS)
        resp.encoding = "utf-8"
        # xml文档解析
        xml_data = xmltodict.parse(resp.text)
        # print(xml_data)
        liat_DM = xml_data['i']['d']
        print(len(liat_DM)) # 抓取到的弹幕数量
        for i in range(len(liat_DM)):
            p = liat_DM[i]['@p']
            pub_time = time.localtime(int(p.split(',')[4]))
            pub_time = time.strftime("%Y-%m-%d %H:%M:%S", pub_time)
            print(pub_time, liat_DM[i]['#text']) # 弹幕发出时间和内容

b = Bili("让子弹飞")
b.get_first_level_comments()
b.get_film_oid()
b.get_film_detail_info()
b.get_not_first_level_comments()
b.get_bullet_chat()

