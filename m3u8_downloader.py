import os
import re
import queue
import requests
import threading
import datetime
from logger import Logger
from response import Response
from Crypto.Cipher import AES
from read_config import Config
from requests.adapters import HTTPAdapter

log = Logger(__name__).get_log


class M3u8Assembly():
    def __init__(self):
        config = Config()
        self.ts_queue = queue.Queue()
        self.max_threads = Response().get_max_threads()
        self.video_format = config.getValue("video_format")
        self.ffmpeg_path = config.getValue("ffmpeg_path")
        self.key_host = Response().get_key_url()

    def set_movie_path(self, value):
        self._movie_path = value

    def set_movie_name(self, value):
        self._movie_name = value

    def set_concatfile(self, value):
        self._concatfile = value

    def set_totals_tasks(self, value):
        self._totals_tasks = value

    def set_output_name(self, value):
        self._output_name = value

    def set_download_tasks(self, value):
        self._download_tasks = value

    def get_finish_tasks(self):
        return self._totals_tasks - self._download_tasks

    def set_finish_tasks(self, value):
        self._finish_tasks = value

    def set_thread_name(self, value):
        self._thread_name = value

    def down_enqueue(self, url, title, movieName):
        # 保存的资源目录
        source_path = self.get_source_abspath()
        name = url.split('/')[-4]
        # m3u8文件的url
        log.info("正在解析：{} {}".format(title, movieName))
        # 获取m3u8文件内容
        m3u8Info = Response().get_requests_rsp(url).decode('gbk')
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
        # 已下载的数量
        download_task = 0
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
        for ts_url in ts_urls:
            ts_name = re.search('([a-zA-Z0-9-]+.ts)', ts_url).group(1).strip()

            # ts_name = ts_url.split("/")[-1]  # ts文件名
            # 只下载不存在的，或者大小为0的文件,
            if ts_name not in ts_list or os.path.getsize(os.path.join(movie_path, ts_name)) == 0:
                download_task += 1
                self.ts_queue.put(
                    [self.key_host+ts_url, key])

                log.debug("\n断点续传 加入任务列表 {}".format(ts_url))
                # 写入下载任务列表
            open(
                concatfile, 'a+').write("file '{}\{}'\n".format(self.get_abspath(concatfile), ts_name))
        log.debug("加载ts列表成功 {} ".format(url))

        self.set_concatfile(concatfile)
        self.set_movie_path(movie_path)
        self.set_totals_tasks(total_tasks)
        self.set_download_tasks(download_task)

        return self.ts_queue

    def run(self, ts_queue):
        isDone = ''
        showText = ''

        # print('当前任务数:{}'.format(tt_name, self._download_tasks))
        tt_name = threading.current_thread().getName()
        while not ts_queue.empty():
            finish_task = self.get_finish_tasks()
            download_task = ts_queue.qsize()
            url, key = self.ts_queue.get()

            # log.info('Dwonload:{} {}/{}'.format(movie_path,
            # self._totals_tasks-download_tasks, self._totals_tasks))
            ts_name = re.search('([a-zA-Z0-9-]+.ts)', url).group(1).strip()
            # log.info("线程:{} 文件:{}\{}  开始下载".format(
            # tt_name, movie_path, ts_name))

            tsInfo = Response().get_requests_rsp(url)

            # 密文长度不为16的倍数，则添加b"0"直到长度为16的倍数
            # # decrypt方法的参数需要为16的倍数，如果不是，需要在后面补二进制"0"
            while len(tsInfo) % 16 != 0:
                tsInfo += b"0"
                log.debug("\n{} 密文长度不为16的倍数".format(url))
            # log.info("正在解密：" + ts_name)
            # 写入文件
            ts_file = os.path.join(self._movie_path, ts_name)

            with open(ts_file, "ab") as file:

                try:
                    # 已下载的数量
                    file.write(self.decrypt_ts(tsInfo, key))
                    downloaded_count = download_task - ts_queue.qsize()
                    self.set_download_tasks(download_task - downloaded_count)
                    finish_task = self.get_finish_tasks()
                    if finish_task == 0:
                        showText = '寻找资源'
                    if finish_task > 0:
                        showText = '正在下载'
                    if finish_task == self._totals_tasks:
                        showText = '下载完成'
                    print('\r'+'[任务 %s.%s %s (%d/%d)]:[%s%s] %.2f%% ' % (self._movie_name, self.video_format, showText,
                                                                         finish_task, self._totals_tasks,
                                                                         '>' *
                                                                         int(60*finish_task /
                                                                             self._totals_tasks),
                                                                         '-' *
                                                                         int(60*self._download_tasks /
                                                                             self._totals_tasks),
                                                                         float(finish_task / self._totals_tasks * 100)), end='')

                    # log.info("保存成功：" + ts_name)
                except Exception as e:
                    log.debug("{}{} {} \n解密失败:{}".format(tt_name,
                                                         url, ts_file, e))

            log.debug("\n{} 文件:{} {} 下载成功".format(
                tt_name, self._movie_path, ts_name))

    def decrypt_ts(self, ts, key):
        # log.info(key)
        # 解密，new有三个参数，
        # 第一个是秘钥（key）的二进制数据，
        # 第二个使用下面这个就好
        # 第三个IV在m3u8文件里URI后面会给出，如果没有，可以尝试把秘钥（key）赋值给IV
        # 获取ts文件二进制数据
        sprytor = AES.new(key, AES.MODE_CBC, IV=key)
        return sprytor.decrypt(ts)

    def get_key(self, url):
        key = Response().get_requests_rsp(url)
        return key

    def merge(self, concatfile, movie_path, name):
        start = datetime.datetime.now().replace(microsecond=0)
        fileName = os.path.join(movie_path, name + '.'+self.video_format)
        m3u8List = self.get_file_abspath(concatfile)
        outputName = self.get_file_abspath(fileName)
        filePath = self.get_abspath(outputName)
        self.set_output_name(outputName)
        os.system("cd {}".format(filePath))
        try:
            # ffmpeg合并命令
            command = "{}  -y -safe 0 -f concat -i {} -bsf:a aac_adtstoasc -c copy {}".format(
                self.ffmpeg_path, m3u8List, outputName)
            log.debug(os.system(command))

        except Exception as e:
            log.info('{} 合并失败 {}'.format(self._thread_name, e))

    def download(self, url, title, movieName):
        start = datetime.datetime.now().replace(microsecond=0)
        self.set_movie_name(movieName)
        ts_queue = self.down_enqueue(
            url, title, movieName)
        threadPools = []
        task_size = self.max_threads if ts_queue.qsize(
        ) > self.max_threads else ts_queue.qsize()
        for i in range(task_size):
            thread_name = 'Thread-'+movieName+'-'+str(i)
            self.set_thread_name(thread_name)
            t = threading.Thread(
                target=self.run, name=thread_name, kwargs={'ts_queue': ts_queue})

            threadPools.append(t)
        for t in threadPools:
            t.start()
        for t in threadPools:
            t.join()
        end = datetime.datetime.now().replace(microsecond=0)
        log.info('\n {} 下载总耗时：{}'.format(movieName,
                                         str(end - start)))
        self.merge(self._concatfile, self._movie_path, self._movie_name)
        over = datetime.datetime.now().replace(microsecond=0)
        log.info('\n {} 合并完成 耗时 {}'.format(
            self._movie_name, str(over - end)))
        if os.path.exists(self._output_name):
            self.del_ts_files()

    def get_file_abspath(self, file):
        path = os.path.abspath('.')
        filePath = os.path.join(path, file)
        return filePath

    def get_abspath(self, file):
        path = os.path.split(os.path.realpath(file))[0]
        return path

    def get_source_abspath(self):
        path = os.path.abspath('.')
        sourcePath = os.path.join(path, "source")
        return sourcePath

    def del_ts_files(self):

        for root, dirs, files in os.walk(self._movie_path):
            for name in files:
                # 指定要删除的格式，这里是jpg 可以换成其他格式
                if name.endswith(".ts") or name.endswith(".txt"):
                    os.remove(os.path.join(root, name))
        log.info("清理缓存文件成功:{}".format(self._movie_path))


if __name__ == '__main__':
    url = "https://aaaaplay.com/20200402/lpYsAmc7/1263kb/hls/index.m3u8"
    m3u8 = M3u8Assembly()
    m3u8.download(url, "国产视频", "20200402")
    # url = "https://aaaaplay.com/20200327/q2PbPe9N/1563kb/hls/index.m3u8"
    # m3u8.download(url, "国产视频", "20200327")
