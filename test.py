import datetime
import os
import re
import threading
import requests
from queue import Queue
# 预下载，获取m3u8文件，读出ts链接，并写入文档
def down():
  # m3u8链接
  url = 'https://ali-video.acfun.cn/mediacloud/acfun/acfun_video/segment/3zf_GAW6nFMuDXrTLL89OZYOZ4mwxGoASH6UcZbsj1_6eAxUxtp3xm8wFmGMNOnZ.m3u8?auth_key=1573739375-474267152-0-a5aa2b6df4cb4168381bf8b04d88ddb1'
  # 当ts文件链接不完整时，需拼凑
  # 大部分网站可使用该方法拼接，部分特殊网站需单独拼接
  base_url = re.split(r"[a-zA-Z0-9-_\.]+\.m3u8", url)[0]
  # print(base_url)
  resp = requests.get(url)
  m3u8_text = resp.text
  # print(m3u8_text)
  # 按行拆分m3u8文档
  ts_queue = Queue(10000)
  lines = m3u8_text.split('\n')
  # 找到文档中含有ts字段的行
  concatfile = 'cache/' + "s" + '.txt'
  for line in lines:
    if '.ts' in line:
      if 'http' in line:
        # print("ts>>", line)
        ts_queue.put(line)
      else:
        line = base_url + line
        ts_queue.put(line)
        # print('ts>>',line)
      filename = re.search('([a-zA-Z0-9-]+.ts)', line).group(1).strip()
      # 一定要先写文件，因为线程的下载是无序的，文件无法按照
      # 123456。。。去顺序排序，而文件中的命名也无法保证是按顺序的
      # 这会导致下载的ts文件无序，合并时，就会顺序错误，导致视频有问题。
      open(concatfile, 'a+').write("file %s\n" % filename)
  return ts_queue,concatfile
# 线程模式，执行线程下载
def run(ts_queue):
  tt_name = threading.current_thread().getName()
  while not ts_queue.empty():
    url = ts_queue.get()
    r = requests.get(url, stream=True)
    filename = re.search('([a-zA-Z0-9-]+.ts)', url).group(1).strip()
    with open('cache/' + filename, 'wb') as fp:
      for chunk in r.iter_content(5242):
        if chunk:
          fp.write(chunk)
    print(tt_name + " " + filename + ' 下载成功')
# 视频合并方法，使用ffmpeg
def merge(concatfile, name):
  try:
    path = 'cache/' + name + '.mp4'
    command = 'ffmpeg -y -f concat -i %s -crf 18 -ar 48000 -vcodec libx264 -c:a aac -r 25 -g 25 -keyint_min 25 -strict -2 %s' % (concatfile, path)
    os.system(command)
    print('视频合并完成')
  except:
    print('合并失败')
if __name__ == '__main__':
  name = input('请输入视频名称：')
  start = datetime.datetime.now().replace(microsecond=0)
  s,concatfile = down()
  # print(s,concatfile)
  threads = []
  for i in range(15):
    t = threading.Thread(target=run, name='th-'+str(i), kwargs={'ts_queue': s})
    threads.append(t)
  for t in threads:
    t.start()
  for t in threads:
    t.join()
  end = datetime.datetime.now().replace(microsecond=0)
  print('下载耗时：' + str(end - start))
  merge(concatfile,name)
  over = datetime.datetime.now().replace(microsecond=0)
  print('合并耗时：' + str(over - end))