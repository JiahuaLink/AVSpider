
import re
import requests
from lxml import etree
import datetime
import readconfig
from urllib.parse import unquote
from threading import *
from m3u8Downloader import m3u8Assembly


nMaxThread = 5
connectlock = BoundedSemaphore(nMaxThread)

class Spider:
    def __init__(self):
        config = readconfig.Config()
        self.base_url = config.getValue("base_url")
        self.key_url = config.getValue("key_url")
        self.menu_link = config.getValue("menu_link")
        self.av_link = config.getValue("av_link")
        self.js_link = config.getValue("js_link")

    def getBaseUrl(self):
        return self.base_url
    def getKeyUrl(self):
        return self.key_url

    def getHtmlInfo(self, url):
        res = requests.get(url).content
        html = etree.HTML(res.decode('utf-8'))
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
        # print(jsURL)
        url = self.base_url+jsURL
        # print("jsURL:"+url)
        return url

    def starts(self):
        menuList = self.getAvMenuBar(self.base_url)
        for i in range(0, len(menuList)):
            title = menuList[i].get("title")
            menuUrl = menuList[i].get("href")
            # print(title, menuUrl)
            avList = self.getAvListInfo(menuUrl)
            for j in range(0, len(avList)):
                connectlock.acquire()
                url = self.getAVUrl(avList[j].get("href"))
                name = avList[j].get("title")
                jsurl = self.getJsUrl(url)
                print("爬取:{}  {}".format(title, name))
                t = AVThread(jsurl, title, name)
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
            # print(finalUrl)
            m3u8Assembly().download(finalUrl,self.title,self.movieName)
        finally:
            connectlock.release() 

    def getPageId(self, url):
        pageId = re.findall(r'/play/(\d+)-*', url)[0]
        return pageId


if __name__ == '__main__':
    spider = Spider()
    spider.starts()
