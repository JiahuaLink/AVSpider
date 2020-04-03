import os
import re
import queue
import requests
import threading
import datetime
from logger import Logger
from Crypto.Cipher import AES
from readconfig import Config
from requests.adapters import HTTPAdapter

log = Logger().get_log


class m3u8Assembly():
    def __init__(self):
        config = Config()
        self.ts_queue = queue.Queue()
        self.key_host = config.getValue("key_url")
        self.max_threads = int(config.getValue("max_threads"))
        self.max_retries = int(config.getValue("max_retries"))
        self.video_format = config.getValue("video_format")
        self.ffmpeg_path = config.getValue("ffmpeg_path")
        self.session = requests.Session()
        self.session.mount(
            'http://', HTTPAdapter(max_retries=self.max_retries))
        self.session.mount(
            'https://', HTTPAdapter(max_retries=self.max_retries))
        self.header = {
            'User-Agen': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4090.0 Safari/537.36 Ed',
            'Referer': 'https://app5277.com/'
        }

    def down(self, url, title, movieName):
        # 保存的文件名
        name = url.split('/')[-4]
        # m3u8文件的url
        log.info("正在解析：{} {}".format(title, movieName))
        # 获取m3u8文件内容
        try:
            m3u8Info = self.session.get(
                url, headers=self.header).content.decode('gbk')
        except:
            log.error("获取{}信息失败".format(movieName))
        # 通过正值表达式获取key和ts的链接
        # key的正则匹配
        k = re.compile(r"\/.*?\.key")
        # ts的正则匹配
        t = re.compile(r".*?\.ts")
        # key的url
        key_url = k.findall(m3u8Info)[0]
        # ts的url列表
        ts_urls = t.findall(m3u8Info)
        # log.info(key_url, ts_urls)
        # 下载key的二进制数据
        # log.info("正在下载key")
        key = self.get_key(self.key_host+key_url)
        # 解密并保存ts
        if not os.path.exists(movieName):
            os.makedirs(movieName)
        concatfile = os.path.join(movieName, "cache" + '.txt')

        # 初始化缓存列表
        if os.path.exists(concatfile):
            os.remove(concatfile)
        ts_list = os.listdir(movieName)
        for ts_url in ts_urls:
            ts_name = re.search('([a-zA-Z0-9-]+.ts)', ts_url).group(1).strip()
            # ts_name = ts_url.split("/")[-1]  # ts文件名
            # 解密，new有三个参数，
            # 第一个是秘钥（key）的二进制数据，
            # 第二个使用下面这个就好
            # 第三个IV在m3u8文件里URI后面会给出，如果没有，可以尝试把秘钥（key）赋值给IV

            # 获取ts文件二进制数据
            if ts_name not in ts_list:
                self.ts_queue.put([self.key_host+ts_url, movieName, key])
                #log.info("{} 文件不存在,加入任务列表".format(ts_name))
            open(
                concatfile, 'a+').write("file '{}\{}'\n".format(self.get_abspath(concatfile), ts_name))
        log.info("{}入队完成".format(name))
        return self.ts_queue, concatfile

    def run(self, ts_queue):
        # 获取已下载列表文件，只下载不存在文件

        tt_name = threading.current_thread().getName()
        while not ts_queue.empty():
            url, movieName, key = self.ts_queue.get()
            ts_name = re.search('([a-zA-Z0-9-]+.ts)', url).group(1).strip()
            log.info("文件:{} 线程{} 开始下载:{}".format(movieName, tt_name, ts_name))
            req = self.session.get(url, headers=self.header)
            req.raise_for_status()
            ts = req.content
            # 密文长度不为16的倍数，则添加b"0"直到长度为16的倍数
            while len(ts) % 16 != 0:
                ts += b"0"
            # log.info("正在解密：" + ts_name)
            # 写入文件
            with open(os.path.join(movieName, ts_name), "ab") as file:
                # # decrypt方法的参数需要为16的倍数，如果不是，需要在后面补二进制"0"
                file.write(self.decrypt_ts(ts, key))

                # log.info("保存成功：" + ts_name)
            log.info("文件:{} 线程:{} {} 下载成功".format(movieName, tt_name, ts_name))

    def decrypt_ts(self, ts, key):

        # log.info(key)
        sprytor = AES.new(key, AES.MODE_CBC, IV=key)
        return sprytor.decrypt(ts)

    def get_key(self, url):
        key = requests.get(url).content
        return key


    def merge(self, concatfile, name):
        fileName = os.path.join(name, name + '.'+self.video_format)
        m3u8List = self.get_file_abspath(concatfile)
        outputName = self.get_file_abspath(fileName)
        filePath = self.get_abspath(outputName)
        os.system("cd {}".format(filePath))
        try:
            command = "{}  -y -safe 0 -f concat -i {} -c copy {}".format(self.ffmpeg_path,
                m3u8List, outputName)
            os.system(command)

            log.info('视频 {}合并完成'.format(outputName))
        except:
            log.info('合并失败')

    def download(self, url, title, movieName):
        start = datetime.datetime.now().replace(microsecond=0)
        ts_queue, concatfile = self.down(url, title, movieName)
        threadPools = []
        for i in range(self.max_threads):
            t = threading.Thread(
                target=self.run, name='th-'+str(i), kwargs={'ts_queue': ts_queue})
            threadPools.append(t)
        for t in threadPools:
            t.start()
        for t in threadPools:
            t.join()
        end = datetime.datetime.now().replace(microsecond=0)
        log.info('下载耗时：' + str(end - start))
        self.merge(concatfile, movieName)
        over = datetime.datetime.now().replace(microsecond=0)
        log.info('合并耗时：' + str(over - end))

    def get_file_abspath(self, file):
        path = os.path.split(os.path.realpath(__file__))

        filePath = os.path.join(path[0], file)
        return filePath

    def get_abspath(self, file):
        path = os.path.split(os.path.realpath(file))[0]
        return path


if __name__ == '__main__':
    url = "https://aaaaplay.com/20200402/lpYsAmc7/1263kb/hls/index.m3u8"
    m3u8 = m3u8Assembly()
    m3u8.download(url, "国产视频", "20200402")
    url = "https://aaaaplay.com/20200327/q2PbPe9N/1563kb/hls/index.m3u8"
    m3u8.download(url, "国产视频", "20200327")
