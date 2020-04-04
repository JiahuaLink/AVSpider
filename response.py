import re
import readconfig
import requests
from urllib.parse import unquote
from lxml import etree
from requests.adapters import HTTPAdapter
from logger import Logger

log = Logger().get_log


class Response():
    '''响应类'''

    def __init__(self):
        config = readconfig.Config()
        self.base_url = config.getValue("base_url")
        self.key_url = config.getValue("key_url")
        self.menu_link = config.getValue("menu_link")
        self.av_link = config.getValue("av_link")
        self.js_link = config.getValue("js_link")
        self.max_threads = int(config.getValue("max_threads"))
        self.max_retries = int(config.getValue("max_retries"))

        self.session = requests.Session()
        self.session.mount(
            'http://', HTTPAdapter(max_retries=self.max_retries))
        self.session.mount(
            'https://', HTTPAdapter(max_retries=self.max_retries))

        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36',
            'Referer': 'https://app5277.com/player/videojs.html'
        }

    def getRequestsRsp(self, url):
        res = ''
        try:
            response = self.session.get(
                url, headers=self.headers, timeout=(3, 7))
            response.raise_for_status()  # 若状态码不是200，抛出HTTPError异常
            # 保证页面编码正确
            res = response.content
        except requests.exceptions.ConnectTimeout as e:
            log.error('请求超时！'.format(e))
        except requests.exceptions.ConnectionError:
            log.error('{}无效地址！'.format(url))
        return res

    def getBaseUrl(self):
        return self.base_url

    def getHeaders(self):
        return self.headers

    def getKeyUrl(self):
        return self.key_url

    def get_max_threads(self):
        return self.max_threads

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

    def get_m3u8_url(self, jsurl):
        jsContent = self.getRequestsRsp(jsurl).decode('UTF-8')
        k1 = re.compile(r"https.*?.m3u8")
        tempUrl = unquote(k1.findall(jsContent)[0])
        m3u8_main_content = self.getRequestsRsp(
            tempUrl).decode('UTF-8')
        k2 = re.compile(r".*?.m3u8")
        m3u8Url = k2.findall(m3u8_main_content)[0]
        finalUrl = '{}{}'.format(self.getKeyUrl(), m3u8Url)
        return finalUrl

    def getAVUrl(self, url):
        return("{}{}".format(self.base_url, url))

    def getJsUrl(self, url):
        html = self.getHtmlInfo(url)
        jsURL = html.xpath(self.js_link)[0].get("src")
        # log.info(jsURL)
        url = self.base_url+jsURL
        # log.info("jsURL:"+url)
        return url
