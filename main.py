#!/usr/bin/env python
# coding: UTF-8
from gevent import monkey
monkey.patch_all()

from amazon import Amazon
from BeautifulSoup import BeautifulSoup
import simplejson
import urllib
import gevent
import sys
import re

from config import *

def getAmazon(isbn):
    result = []
    amazon = Amazon(access_key, access_secret, associate_tag)
    xml = amazon.itemLookup(isbn, SearchIndex='Books', IdType='ISBN', ReviewPage='1', ResponseGroup='Reviews')

    soup = BeautifulSoup(xml)
    if soup.find('hasreviews').getText() == 'false':
        return result
    url = soup.find('iframeurl').contents[0]

    iframe = urllib.urlopen(url.replace('&amp;', '&'))
    soup = BeautifulSoup(iframe)
    for div in soup.findAll('div', {'style': 'margin-left:0.5em;'}):
        for i in div.findAll('div'):
            i.replaceWith('')
        result.append(div.getText())
    return result

def getBooklog(isbn):
    result = []
    regex = re.compile(r'showDescription\(([0-9]*)\);return false;')

    html = urllib.urlopen('http://booklog.jp/item/1/' + isbn)
    soup = BeautifulSoup(html)

    review = int(soup.find('span', {'class': 'em1 count'}).getText())
    request = []
    for i in range(1, review / 25 + 2):
        request.append(('http://booklog.jp/item/1/' + isbn + '?page=' + str(i), regex, []))

    jobs = [gevent.spawn(fetchBooklog, req) for req in request]
    gevent.joinall(jobs)

    for req in request:
        result += req[2]
    return result

def fetchBooklog(req):
    url, regex, result = req

    html = urllib.urlopen(url)
    soup = BeautifulSoup(html)

    for i in soup.findAll('div', {'class': 'summary'}):
        review = i.p.getText()
        if review.endswith('続きを読む&nbsp;&#187;'.decode('UTF-8')):
            onclick = i.a['onclick']
            review_id = regex.search(onclick).group(1)

            json = urllib.urlopen('http://booklog.jp/json/review/' + review_id)
            review_json = simplejson.load(json)
            review = review_json[review_id]
        result.append(review)

def getBookmeter(isbn):
    result = []

    html = urllib.urlopen('http://book.akahoshitakuya.com/bl/' + isbn + '?t=c&p=0')
    soup = BeautifulSoup(html)

    navi = soup.find('div', {'class': 'page_navis'})
    url = navi.findAll('a')[-1]['href']
    page = int(re.search('/bl/[0-9]*\?p=([0-9]*)&t=c', url).group(1))

    request = []
    for i in range(0, page + 1):
        request.append(('http://book.akahoshitakuya.com/bl/' + isbn + '?t=c&p=' + str(i), []))

    jobs = [gevent.spawn(fetchBookmeter, req) for req in request]
    gevent.joinall(jobs)

    for req in request:
        result += req[1]
    return result

def fetchBookmeter(req):
    url, result = req

    html = urllib.urlopen(url)
    soup = BeautifulSoup(html)

    for i in soup.findAll('div', {'class': 'log_list_comment'}):
        result.append(i.getText())

def morphologic(req):
    sentence, dic = req

    params = urllib.urlencode({'appid': yahoo_id, 'results': 'uniq', 'filter': '9', 'responce': 'surface','sentence': sentence})
    req = urllib.urlopen('http://jlp.yahooapis.jp/MAService/V1/parse', params)
    soup = BeautifulSoup(req)
    for i in soup.findAll('surface'):
        surface = i.getText().encode('UTF-8')
        if dic.has_key(surface):
            dic[surface] += 1
        else:
            dic[surface] = 1

if __name__ == '__main__':
    form = cgi.FieldStorage()
    isbn = form['isbn'].value
    reviews = [i.encode('UTF-8') for i in getAmazon(isbn) + getBooklog(isbn) + getBookmeter(isbn)]

    request = []
    sentence = ''
    for i in reviews:
        if len(sentence + i) < 10000:
            sentence += i + '\n'
        else:
            request.append((sentence, {}))
            sentence = i
    request.append((sentence, {}))

    jobs = [gevent.spawn(morphologic, req) for req in request]
    gevent.joinall(jobs)

    dic = {}
    for req in request:
        for key, value in req[1].items():
            if dic.has_key(key):
                dic[key] += value
            else:
                dic[key] = value

    keys = sorted(dic, key=dic.get, reverse=True)
    tags = ''
    count = min(50, len(keys))
    font_step = (20.0 - 10.0) / (dic[keys[0]] - dic[keys[count]])
    for i in range(0, count):
        font_size = 10 + (dic[keys[i]] - dic[keys[count]]) * font_step
        tags += '<a href="#" class="tag-link-%d" title="%d件のトピック" style="font-size: %fpt;">%s</a>' % (i, dic[keys[i]], font_size, keys[i])

    print '''
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <script type="text/javascript" src="swfobject.js"></script>
    </head>
    <body>
        <div id="tags">
            <p>%s</p>
            <script type="text/javascript">
                var cloud = new SWFObject("tagcloud.swf", "tagcloudflash", "800", "600", "9", "#ffffff");
                cloud.addParam("allowScriptAccess", "always");
                cloud.addVariable("tcolor", "0x333333");
                cloud.addVariable("tcolor2", "0x888888");
                cloud.addVariable("hicolor", "0xdddddd");
                cloud.addVariable("tspeed", "100");
                cloud.addVariable("distr", "true");
                cloud.addVariable("mode", "tags");
                cloud.addVariable("tagcloud", "%s");
                cloud.write("tags");
            </script>
        </div>
    </body>
</html>''' % (tags, urllib.quote_plus('<tags>%s</tags>' % tags))
