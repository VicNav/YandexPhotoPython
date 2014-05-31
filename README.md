# Доступ к api Яндекс.Фоток на Питоне


	import ya


	fotki = YandexFotki('Login-to-Yandex-Photo', token = 'Token-to-Yandex-Photo')
	# получить сервисный документ
	print fotki.servicedoc


	# создать альбом
	album = Album(fotki)
	album.title = u'проверка'
	album.save()

	# print album
	# print album.linkSelf


	# получить список альбомов
	albums = fotki.getAlbums()
	print albums
	for album in albums:
		print album


	# переименовать альбом
	album.title = '12345'
	print album.save()


	# удалить альбом
	print album.delete()


	# Показать фото из альбома
	photos = album.photos()
	for photo in photos:
		print photo


	# Загрузить фото
	f = open('1.jpg', 'rb')
	body = f.read()
	f.close()

	photo = Photo(fotki)
	photo.upload(body, album.linkPhotos)
	photo.title = u'фоточка'
	photo.summary = u'красивая фоточка'
	photo.save()
	# print photo


	# получить ссылку определённого размера
	print photo.img['XL']


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
