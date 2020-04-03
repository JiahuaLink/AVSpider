
import re
import requests
from lxml import etree
import datetime
import readconfig
from urllib.parse import unquote
from threading import *
from m3u8Downloader import m3u8Assembly
from logger import Logger


nMaxThread = 10
connectlock = BoundedSemaphore(nMaxThread)


class Spider:
    def __init__(self):
        config = readconfig.Config()
        self.base_url = config.getValue("base_url")
        self.key_url = config.getValue("key_url")
        self.menu_link = config.getValue("menu_link")
        self.av_link = config.getValue("av_link")
        self.js_link = config.getValue("js_link")
        self.session = requests.Session()
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36',
            'Referer': 'https://app5277.com/player/videojs.html'
        }

    def getRequestsRsp(self, url):
        res = ''
        try:
            response = self.session.get(url, headers=self.headers,timeout=(3,7))
            response.raise_for_status() #若状态码不是200，抛出HTTPError异常
            response.encoding = response.apparent_encoding  #保证页面编码正确
            res = response.content.decode('utf-8')
        except requests.exceptions.ConnectTimeout:
            log.error('请求超时！')
        except requests.exceptions.ConnectionError:
            log.error('{}无效地址！'.format(url))
        return res

    def getBaseUrl(self):
        return self.base_url
    def getHeaders(self):
        return self.headers
    def getKeyUrl(self):
        return self.key_url

    def getHtmlInfo(self, url):
        res = self.getRequestsRsp(url)
        html = etree.HTML(res)
        return html

    def getAvMenuBar(self, url):
        html = self.getHtmlInfo(url)
        menuList = html.xpath(self.menu_link)
        return menuList

    def getAvListInfo(self, url):
        url = self.base_url+url
        html = self.getHtmlInfo(url)
        avList = html.xpath(self.av_link)
        return avList

    def getAVUrl(self, url):
        return("{}{}".format(self.base_url, url))

    def getJsUrl(self, url):
        html = self.getHtmlInfo(url)
        jsURL = html.xpath(self.js_link)[0].get("src")
        # log.info(jsURL)
        url = self.base_url+jsURL
        # log.info("jsURL:"+url)
        return url

    def starts(self):
        menuList = self.getAvMenuBar(self.base_url)
        for menu in menuList:
            title = menu.get("title")
            menuUrl = menu.get("href")
            log.info("{} {}".format(title, menuUrl))
            avList = self.getAvListInfo(menuUrl)
            for av in avList:
                connectlock.acquire()
                url = self.getAVUrl(av.get("href"))
                name = av.get("title")
                jsurl = self.getJsUrl(url)
                log.info("爬取:{}  {}".format(title, name))
                t = AVThread(jsurl, title.strip(), name.strip())
                t.start()


class AVThread(Thread):

    def __init__(self, url, title, movieName):
        Thread.__init__(self)
        self.jsurl = url
        self.movieName = movieName
        self.title = title

    def run(self):
        try:
            jsContent = requests.get(self.jsurl).content.decode('utf-8')
            k1 = re.compile(r"https.*?.m3u8")
            tempUrl = unquote(k1.findall(jsContent)[0])
            m3u8_main_content = requests.get(tempUrl).content.decode('utf-8')
            k2 = re.compile(r".*?.m3u8")
            m3u8Url = k2.findall(m3u8_main_content)[0]
            finalUrl = '{}{}'.format(Spider().getKeyUrl(), m3u8Url)
            # log.info(finalUrl)
            m3u8Assembly().download(finalUrl, self.title, self.movieName)
        finally:
            connectlock.release()

    def getPageId(self, url):
        pageId = re.findall(r'/play/(\d+)-*', url)[0]
        return pageId


if __name__ == '__main__':
    log = Logger().get_log
    spider = Spider()
    spider.starts()
