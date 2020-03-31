# AVSpider
AV catch tools
批量爬取小视频
流程：
1 
GET https://app5277.com
xpath获取分类 //ul[contains(@class,"nav nav-inline padding-small-top nav-menu")]//li/a
返回 /play/6421-1-1.html

2
构造 GET https://app5277.com/play/6421-1-1.html
xpath 获取js链接 (目的获取m3u8视频链接）

3
构造
GET  https://app5277.com/upload/playdata/20200328/7344/7344.js
返回
var mac_flag='play',mac_link='/play/7344-{src}-{num}.html', mac_name='c2020328_9 ',mac_from='m3u8',mac_server='no'
,mac_note='',mac_url=unescape('https%3A%2F%2Faaaaplay.com%2F20200327%2F7YtHjrzY%2Findex.m3u8');

4
正则提取unescape('https%3A%2F%2Faaaaplay.com%2F20200327%2F7YtHjrzY%2Findex.m3u8');
获得https%3A%2F%2Faaaaplay.com%2F20200327%2F7YtHjrzY%2Findex.m3u8
urldecode 解码
返回 https://aaaaplay.com/20200327/7YtHjrzY/index.m3u8

5
获取m3u8 base链接
https://aaaaplay.com/20200327/7YtHjrzY/index.m3u8
GET https://aaaaplay.com/20200327/7YtHjrzY/index.m3u8
返回 /20200327/7YtHjrzY/1163kb/hls/index.m3u8

6 
获取解密的Key
GET https://aaaaplay.com/20200327/7YtHjrzY/1163kb/hls/index.m3u8
返回 key #EXT-X-KEY:METHOD=AES-128,URI="/20200327/7YtHjrzY/1163kb/hls/key.key"
正则提取Key_Url
GET https://aaaaplay.com/20200327/7YtHjrzY/1163kb/hls/key.key
返回 c028f11e9b8b9b8e

根据c028f11e9b8b9b8e 解密m3u8 

最后调用该M3U8拼接下载
