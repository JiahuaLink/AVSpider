# AVSpider
AV catch tools
批量爬取小视频
流程：


获取 /play/6421-1-1.html
pageId 7344

构造
GET  https://app5277.com/upload/playdata/20200328/7344/7344.js
返回
var mac_flag='play',mac_link='/play/7344-{src}-{num}.html', mac_name='c2020328_9 ',mac_from='m3u8',mac_server='no'
,mac_note='',mac_url=unescape('https%3A%2F%2Faaaaplay.com%2F20200327%2F7YtHjrzY%2Findex.m3u8');

正则提取unescape('https%3A%2F%2Faaaaplay.com%2F20200327%2F7YtHjrzY%2Findex.m3u8');
获得https%3A%2F%2Faaaaplay.com%2F20200327%2F7YtHjrzY%2Findex.m3u8

urldecode 解码
返回 https://aaaaplay.com/20200327/7YtHjrzY/index.m3u8


获取m3u8 base
https://aaaaplay.com/20200327/7YtHjrzY/index.m3u8

GET https://aaaaplay.com/20200327/7YtHjrzY/index.m3u8
返回 /20200327/7YtHjrzY/1163kb/hls/index.m3u8

GET https://aaaaplay.com/20200327/7YtHjrzY/1163kb/hls/index.m3u8
返回 key #EXT-X-KEY:METHOD=AES-128,URI="/20200327/7YtHjrzY/1163kb/hls/key.key"

GET https://aaaaplay.com/20200327/7YtHjrzY/1163kb/hls/key.key
返回 c028f11e9b8b9b8e

根据c028f11e9b8b9b8e 解密m3u8 

最后调用买M3U8拼接下载
