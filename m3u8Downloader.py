import os
import re
import requests
from Crypto.Cipher import AES
from readconfig import Config


class m3u8Assembly():
    def __init__(self):
        config = Config()
        self.key_host = config.getValue("key_url")

    def download(self, url, title, movieName):
        # 保存的mp4文件名
        name = self.getFilePath(title, movieName)
        # m3u8文件的url
        print("正在解析：{} {}".format(title, movieName))
        # 获取m3u8文件内容
        m3u8Info=requests.get(url).content.decode('gbk')
        # 通过正值表达式获取key和ts的链接
        # key的正则匹配
        k=re.compile(r"\/.*?\.key")
        # ts的正则匹配
        t=re.compile(r".*?\.ts")
        # key的url
        key_url=k.findall(m3u8Info)[0]
        # ts的url列表
        ts_urls=t.findall(m3u8Info)
        # print(key_url, ts_urls)
        # 下载key的二进制数据
        # print("正在下载key")
        key=requests.get(self.key_host+key_url).content
        # print(key)

        # 解密并保存ts
        for ts_url in ts_urls:
            ts_name=ts_url.split("/")[-1]  # ts文件名
            # 解密，new有三个参数，
            # 第一个是秘钥（key）的二进制数据，
            # 第二个使用下面这个就好
            # 第三个IV在m3u8文件里URI后面会给出，如果没有，可以尝试把秘钥（key）赋值给IV
            sprytor=AES.new(key, AES.MODE_CBC, IV=key)
            # 获取ts文件二进制数据
            print("正在下载：{}--{}--{}" .format(title, movieName,ts_name))
            ts=requests.get(self.key_host+ts_url).content
            # 密文长度不为16的倍数，则添加b"0"直到长度为16的倍数
            while len(ts) % 16 != 0:
                ts += b"0"

            # print("正在解密：" + ts_name)
            # 写入mp4文件
            with open(name, "ab") as file:
                # # decrypt方法的参数需要为16的倍数，如果不是，需要在后面补二进制"0"
                file.write(sprytor.decrypt(ts))
                print("保存成功：" + ts_name)
        print(name, "下载完成")

    def getFilePath(self, title, name):

        root_dir=os.path.dirname(os.path.abspath(__file__))
        path=os.path.join(root_dir, 'source', title, name+'.mp4')

        if not os.path.isdir(os.path.split(path)[0]):
            os.makedirs(os.path.split(path)[0])
        return path


if __name__ == '__main__':
    url="https://aaaaplay.com/20200327/7YtHjrzY/1163kb/hls/index.m3u8"
    m3u8=m3u8Assembly()
    m3u8.download(url, "test", "1")
