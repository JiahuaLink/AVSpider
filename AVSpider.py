
import re
import queue
import datetime
import threading
from threading import *
from logger import Logger
from response import Response
from m3u8Downloader import m3u8Assembly


class Spider:
    '''一只小爬虫'''

    def __init__(self):
        self.rsp = Response()
        self.av_queue = queue.Queue()
        self.max_threads = 5

    def run(self, av_queue):
        tt_name = threading.current_thread().getName()
        while not av_queue.empty():
            jsurl, menu_title, movieName = self.av_queue.get()
            m3u8Url = self.rsp.get_m3u8_url(jsurl)
            log.debug("{} 开始爬取视频:{}".format(
                tt_name, m3u8Url))
            try:
                # log.info(finalUrl)
                m3u8Assembly().download(m3u8Url, menu_title, movieName)
            except Exception as e:
                log.error("爬取失败 {}".format(e))

    def spider_enqueue(self):
        start = datetime.datetime.now().replace(microsecond=0)
        menuList = self.rsp.getAvMenuBar(self.rsp.getBaseUrl())
        for menu in menuList[0:1]:
            menu_title = menu.get("title")
            menuUrl = menu.get("href")
            log.info("{} {}".format(menu_title, menuUrl))
            avList = self.rsp.getAvListInfo(menuUrl)

            for av in avList[0:3]:
                url = self.rsp.getAVUrl(av.get("href"))
                name = av.get("title")
                log.debug("爬取:{}  {}".format(menu_title, name))
                jsurl = self.rsp.getJsUrl(url)
                self.av_queue.put([jsurl, menu_title.strip(), name.strip()])
        return self.av_queue

    def start(self):
        av_queue = self.spider_enqueue()
        threadPools = []
        for i in range(self.max_threads):
            t = threading.Thread(
                target=self.run, name='AV-'+str(i), kwargs={'av_queue': av_queue})
            threadPools.append(t)
        for t in threadPools:
            t.start()
        for t in threadPools:
            t.join()
    # def getPageId(self, url):
    #     pageId = re.findall(r'/play/(\d+)-*', url)[0]
    #     return pageId


if __name__ == '__main__':
    log = Logger(__name__).get_log
    spider = Spider()
    spider.start()
