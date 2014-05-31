#!/usr/bin/python
# coding:utf-8


from lxml import etree as ET
import urlparse
import httplib
import urllib
import json
import os
import re

NSMAP = {
    'atom': 'http://www.w3.org/2005/Atom',
    'app': 'http://www.w3.org/2007/app',
    'f': 'yandex:fotki',
}

class YandexFotki(object):
    ERROR = []

    def __init__(self, username = None, token = None):

        self.username = username
        self.token = 'OAuth %s' % token

        if username:
            self.servicedoc = self.loadServicedoc(username)
        else:
            self.servicedoc = {}


    # Загрузка сервисного документа
    def loadServicedoc(self, username):
        service = {}
        url = 'http://api-fotki.yandex.ru/api/users/%s/' % urllib.quote(username)
        xml = self._open(url)
        root = ET.fromstring(xml)
        for el in root.xpath('//app:workspace/app:collection', namespaces=NSMAP):
            service[el.attrib['id']] = el.attrib['href']
        return service


    # Загрузка списка альбомов
    def getAlbums(self):
        albums = []
        url = self.servicedoc['album-list']
        xml = self._open(url)
        root = ET.fromstring(xml)
        for entry in root.xpath('//atom:entry', namespaces=NSMAP):
            album = Album(self)
            album.dom(entry)
            albums.append(album)
        return albums


    # HTTP-запрос к серверу
    def _open(self, url, method = None, headers = {}, raw_data = ''):
        
        USER_AGENT = 'Python Yandex API Client/0.1'

        parsed = urlparse.urlparse(url)
        assert parsed.scheme.lower() == 'http', 'Only http requests are supported by now'

        selector = parsed.path
        if parsed.query:
            selector += '?' + parsed.query

        if method:
            request_method = method
        elif raw_data:
            request_method = 'POST'
        else:
            request_method = 'GET'

        try:
            conn = httplib.HTTPConnection(parsed.netloc)

            conn.putrequest(request_method, selector, skip_host = True, skip_accept_encoding = True)
            conn.putheader('User-Agent', USER_AGENT)
            conn.putheader('Host', parsed.hostname)

            if self.token:
                conn.putheader('Authorization', self.token)

            for header, value in headers.items():
                conn.putheader(header, value)

            if raw_data:
                conn.putheader('Content-Length', len(raw_data))
                conn.endheaders()
                conn.send(raw_data)
            else:
                conn.endheaders()

            response = conn.getresponse()

            conn.close()
            if 200 <= response.status < 300:
                return response.read()
            else:
                self.ERROR = '%d %s' % (response.status, response.read())
                print self.ERROR
                return False

        except httplib.HTTPException, e:
            raise e



class Album(object):
    ya = None       # объект YandexFotki с загруженным сервисдокументом
    entry = None    # объект lxml
    linkSelf = ''   # ссылка на альбом в Яндекс.фотки
    linkAlbum = ''  # ссылка на родительский альбом
    linkPhotos = '' # ссылка на список фотографий этого альбома
    title = ''      # название альбома
    summary = ''    # описание альбома
    password = ''   # пароль
    imageCount = 0  # количество изображений
    protected = 'false'


    def __init__(self, ya):
        self.ya = ya


    # Загрузка альбомa
    def load(self, url):
        self.entry = self.ya._open(url)
        self.dom(self.entry)
        return self


    # сохранение альбомa
    def save(self):
        method = 'PUT'
        if not self.entry:
            method = 'POST'
            xml = u'<entry xmlns="http://www.w3.org/2005/Atom" xmlns:f="yandex:fotki">\n'
            xml += u'<title></title>\n<summary></summary>\n<f:password></f:password>\n<f:protected value="false" />\n</entry>\n'
            self.entry = ET.fromstring(xml)
            self.linkSelf = self.ya.servicedoc['album-list']

        self.entry.xpath('//atom:title', namespaces=NSMAP)[0].text = self.title
        if self.summary:
            self.entry.xpath('//atom:summary', namespaces=NSMAP)[0].text = self.summary
        if self.password:
            self.entry.xpath('//atom:password', namespaces=NSMAP)[0].text = self.password
        if self.protected:
            self.entry.xpath('//f:protected', namespaces=NSMAP)[0].attrib['value'] = self.protected 
        if self.linkAlbum:
            self.entry.xpath('//atom:link[@rel="album"]', namespaces=NSMAP)[0].attrib['href'] = self.linkAlbum

        xml = ET.tostring(self.entry, pretty_print=True, encoding='utf-8')

        # print self.linkSelf
        # print xml

        xml = self.ya._open(self.linkSelf, method=method, raw_data=xml, \
            headers = {'Content-Type': 'application/atom+xml; charset=utf-8; type=entry'})

        self.dom(ET.fromstring(xml))
        return self


    # Удаление альбома
    def delete(self):
        return self.ya._open(self.linkSelf, method='DELETE')


    def dom(self, dom):
        self.entry = dom

        title = self.entry.xpath('./atom:title/text()', namespaces=NSMAP)
        summary = self.entry.xpath('./atom:summary/text()', namespaces=NSMAP)
        password = self.entry.xpath('./atom:password/text()', namespaces=NSMAP)
        imageCount = self.entry.xpath('./f:image-count/@value', namespaces=NSMAP)
        linkSelf = self.entry.xpath('./atom:link[@rel="self"]/@href', namespaces=NSMAP)
        linkAlbum = self.entry.xpath('./atom:link[@rel="album"]/@href', namespaces=NSMAP)
        linkPhotos = self.entry.xpath('./atom:link[@rel="photos"]/@href', namespaces=NSMAP)

        self.title = title and title[0] or ''
        self.summary = summary and summary[0] or ''
        self.password = password and password[0] or ''
        self.imageCount = imageCount and imageCount[0] or 0
        self.linkSelf = linkSelf and linkSelf[0] or ''
        self.linkAlbum = linkAlbum and linkAlbum[0] or ''
        self.linkPhotos = linkPhotos and linkPhotos[0] or ''

        return self


    def photos(self):
        photos = []
        xml = self.ya._open(self.linkPhotos)
        # print xml
        root = ET.fromstring(xml)
       
        for entry in root.xpath('./atom:entry', namespaces=NSMAP):
            p = Photo(self.ya, entry)
            photos.append(p)
        return photos


    def __str__(self):
        return '%s (%d) %s' % (self.title.encode('utf-8'), int(self.imageCount), self.linkSelf)


    def toxml(self):
        return ET.tostring(self.entry, pretty_print=True, encoding='utf-8')



class Photo(object):
    ya = None       # объект YandexFotki с загруженным сервисдокументом
    entry = None    # объект lxml
    linkSelf = ''   # ссылка на фото в Яндекс.фотки
    linkAlbum = ''  # ссылка на альбом
    title = ''      # название фото
    summary = ''    # описание фото
    xxx = False     # для взрослых
    disableComments = False  # флаг запрета комментариев
    img = {}        # ссылки на фото разных размеров
    access = 'public'


    def __init__(self, ya, entry=None):
        self.ya = ya
        if entry:
            self.dom(entry)

    def dom(self, dom):
        self.entry = dom

        title = self.entry.xpath('./atom:title/text()', namespaces=NSMAP)
        summary = self.entry.xpath('./atom:summary/text()', namespaces=NSMAP)
        linkSelf = self.entry.xpath('./atom:link[@rel="self"]/@href', namespaces=NSMAP)
        linkAlbum = self.entry.xpath('./atom:link[@rel="album"]/@href', namespaces=NSMAP)
        xxx = self.entry.xpath('./f:xxx/@value', namespaces=NSMAP)
        disableComments = self.entry.xpath('./f:disable_comments/@value', namespaces=NSMAP)

        imgs = self.entry.xpath('./f:img', namespaces=NSMAP)
        for img in imgs:
            size = img.xpath('@size', namespaces=NSMAP)
            href = img.xpath('@href', namespaces=NSMAP)
            self.img[size[0]]=href[0]

        self.title = title and title[0] or ''
        self.summary = summary and summary[0] or ''
        self.linkSelf = linkSelf and linkSelf[0] or ''
        self.linkAlbum = linkAlbum and linkAlbum[0] or ''
        if xxx and xxx[0]=='true':
            self.xxx = True
        if disableComments and disableComments[0]=='true':
            self.disableComments = True

        return self


    def upload(self, body, album=None):
        if album:
            self.linkAlbum = album
        if not self.linkAlbum:
            self.linkAlbum = self.ya.servicedoc['photo-list']

        xml = self.ya._open(self.linkAlbum, method='POST', raw_data=body, \
        headers = {'Content-Type': 'image/jpeg'})
        # print xml
        entry = ET.fromstring(xml)
        self.dom(entry)
        return self


    def save(self):
        if self.title:
            self.entry.xpath('./atom:title', namespaces=NSMAP).text = self.title
        if self.summary:
            self.entry.xpath('./atom:summary', namespaces=NSMAP).text = self.summary
        if self.xxx:
            self.entry.xpath('./f:xxx', namespaces=NSMAP).attrib['value'] = self.xxx
        if self.access:
            self.entry.xpath('./f:access', namespaces=NSMAP).attrib['value'] = self.access
        if self.disableComments:
            self.entry.xpath('./f:disable_comments', namespaces=NSMAP).attrib['value'] = self.disableComments
        if self.linkAlbum:
            self.entry.xpath('./atom:link[@rel="album"]', namespaces=NSMAP).attrib['href'] = self.linkAlbum

        xml = ET.tostring(self.entry, pretty_print=True, encoding='utf-8')
        # print xml

        self.entry = self.ya._open(self.linkSelf, method='PUT', raw_data=xml, \
            headers = {'Content-Type': 'application/atom+xml; charset=utf-8; type=entry'})
        return self


    def delete(self):
        return self.ya._open(self.linkSelf, method='DELETE')


    def __str__(self):
        return '%s %s' % (self.title.encode('utf-8'), self.img['orig'])


    def toxml(self):
        return ET.tostring(self.entry, pretty_print=True, encoding='utf-8')


if __name__ == '__main__':
    print 'ya'

    # fotki = YandexFotki('Login-to-Yandex-Photo', token = 'Token-to-Yandex-Photo')
    # получить сервисный документ
    # print fotki.servicedoc

    # получить список альбомов
    # albums = fotki.getAlbums()
    # print albums
    # for album in albums:
    #     print album

    # переименовать альбом
    # album = albums[0]
    # album.title = '12345'
    # print album.save()

    # удалить альбом
    # print album.delete()

    # создать альбом
    # album = Album(fotki)
    # album.title = u'проверка'
    # album.save()

    # print album
    # print album.linkSelf

    # Показать фото из альбома
    # photos = album.photos()
    # for photo in photos:
    #     print photo

    # Загрузить фото
    # f = open('1.jpg', 'rb')
    # body = f.read()
    # f.close()

    # photo = Photo(fotki)
    # photo.upload(body, album.linkPhotos)
    # photo.title = u'фоточко'
    # photo.save()
    # print photo


    # получить ссылку определённого размера
    # print photo.img['XL']

    # размеры:
    # XXXS  50 квадрат
    # XXS   75 квадрат
    # XS    100
    # S     150
    # M     300
    # L     500
    # XL    800
    # XXL  1024
    # XXXL 1280
    # orig
