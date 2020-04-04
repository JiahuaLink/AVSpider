import os
import re
import queue
import requests
import threading
import datetime
from tqdm import tqdm 


from logger import Logger
from response import Response
from Crypto.Cipher import AES
from readconfig import Config
from requests.adapters import HTTPAdapter

log = Logger(__name__).get_log


class m3u8Assembly():
    def __init__(self):
        config = Config()
        self.ts_queue = queue.Queue()
        self.max_threads = Response().get_max_threads()
        self.video_format = config.getValue("video_format")
        self.ffmpeg_path = config.getValue("ffmpeg_path")
        self.key_host = Response().getKeyUrl()

    def down(self, url, title, movieName):
        # 保存的资源目录
        source_path = self.get_source_abspath()

        name = url.split('/')[-4]
        # m3u8文件的url
        log.info("正在解析：{} {}".format(title, movieName))
        # 获取m3u8文件内容
        log.info("开始解析:{}".format(url))
        m3u8Info = Response().getRequestsRsp(url).decode('gbk')
        # 通过正值表达式获取key和ts的链接
        # key的正则匹配
        k = re.compile(r"\/.*?\.key")
        # ts的正则匹配
        t = re.compile(r".*?\.ts")
        # key的url

        key_url = k.findall(m3u8Info)[0]
        # ts的url列表
        ts_urls = t.findall(m3u8Info)
        # 记录任务总数
        total_tasks = len(ts_urls)
        self.set_totals_tasks(total_tasks)
        # log.info(key_url, ts_urls)
        # 下载key的二进制数据
        # log.info("正在下载key")
        key = self.get_key(self.key_host+key_url)
        # 解密并保存ts
        # 保存的文件名
        movie_path = os.path.join(source_path, movieName)
        if not os.path.exists(movie_path):
            os.makedirs(movie_path)
        concatfile = os.path.join(movie_path, name + '.txt')

        # 初始化缓存列表
        if os.path.exists(concatfile):
            os.remove(concatfile)
        ts_list = os.listdir(movie_path)
        download_count = 0
        for ts_url in ts_urls:
            ts_name = re.search('([a-zA-Z0-9-]+.ts)', ts_url).group(1).strip()
            # ts_name = ts_url.split("/")[-1]  # ts文件名
            # 解密，new有三个参数，
            # 第一个是秘钥（key）的二进制数据，
            # 第二个使用下面这个就好
            # 第三个IV在m3u8文件里URI后面会给出，如果没有，可以尝试把秘钥（key）赋值给IV

            # 获取ts文件二进制数据
            if ts_name not in ts_list:
                self.ts_queue.put([self.key_host+ts_url, movie_path, key])

                # log.info("断点续传, {}\{} 加入任务列表".format(movie_path, ts_name))
            open(
                concatfile, 'a+').write("file '{}\{}'\n".format(self.get_abspath(concatfile), ts_name))
        log.info("{} 分析完成".format(url))
        return self.ts_queue, movie_path, concatfile

    def set_totals_tasks(self, value):
        self._totals_tasks = value

    def run(self, ts_queue):
        # 获取已下载列表文件，只下载不存在文件
        download_tasks = ts_queue.qsize()
        process_bar = tqdm(total=self._totals_tasks, initial=self._totals_tasks -
                           download_tasks, desc='Download')
        tt_name = threading.current_thread().getName()
        while not ts_queue.empty():
            
            url, movie_path, key = self.ts_queue.get()
            
            ts_name = re.search('([a-zA-Z0-9-]+.ts)', url).group(1).strip()
            # log.info("线程:{} 文件:{}\{}  开始下载".format(
            #     tt_name, movie_path, ts_name))
            try:
                tsInfo = Response().getRequestsRsp(url)
            except Exception as e:
                log.info("{} 请求失败 {}".format(url, e))

            # 密文长度不为16的倍数，则添加b"0"直到长度为16的倍数
            while len(tsInfo) % 16 != 0:
                tsInfo += b"0"
            # log.info("正在解密：" + ts_name)
            # 写入文件
            with open(os.path.join(movie_path, ts_name), "ab") as file:
                # # decrypt方法的参数需要为16的倍数，如果不是，需要在后面补二进制"0"
                try:
                    file.write(self.decrypt_ts(tsInfo, key))
                    process_bar.update(10)
                    tqdm.write("Done task %" % ts_name)
                except Exception as e:
                    log.info("{} ts_name 解密失败：{}".format(url,ts_name, e))
                # log.info("保存成功：" + ts_name)
            # log.info("线程:{} 文件:{} {} 下载成功".format(
            #     movie_path, tt_name, ts_name))
            
    def decrypt_ts(self, ts, key):

        # log.info(key)
        sprytor = AES.new(key, AES.MODE_CBC, IV=key)
        return sprytor.decrypt(ts)

    def get_key(self, url):
        key = Response().getRequestsRsp(url)
        return key

    def merge(self, concatfile, movie_path, name):
        fileName = os.path.join(movie_path, name + '.'+self.video_format)
        m3u8List = self.get_file_abspath(concatfile)
        outputName = self.get_file_abspath(fileName)
        filePath = self.get_abspath(outputName)
        os.system("cd {}".format(filePath))
        try:
            command = "{}  -y -safe 0 -f concat -i {} -c copy {}".format(self.ffmpeg_path,
                                                                         m3u8List, outputName)
            os.system(command)
            log.info('视频 {} 合并完成'.format(outputName))
        except Exception as e:
            log.info('合并失败 {}'.format(e))

    def download(self, url, title, movieName):
        start = datetime.datetime.now().replace(microsecond=0)
        ts_queue, movie_path, concatfile = self.down(url, title, movieName)
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

        self.merge(concatfile, movie_path, movieName)
        over = datetime.datetime.now().replace(microsecond=0)
        log.info('合并耗时：' + str(over - end))

    def get_file_abspath(self, file):
        path = os.path.split(os.path.realpath(__file__))
        filePath = os.path.join(path[0], file)
        return filePath

    def get_abspath(self, file):
        path = os.path.split(os.path.realpath(file))[0]
        return path

    def get_source_abspath(self):
        path = os.path.split(os.path.realpath(__file__))
        sourcePath = os.path.join(path[0], "source")
        return sourcePath


if __name__ == '__main__':
    url = "https://aaaaplay.com/20200402/lpYsAmc7/1263kb/hls/index.m3u8"
    m3u8 = m3u8Assembly()
    m3u8.download(url, "国产视频", "20200402")
    # url = "https://aaaaplay.com/20200327/q2PbPe9N/1563kb/hls/index.m3u8"
    # m3u8.download(url, "国产视频", "20200327")
