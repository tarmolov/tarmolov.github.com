---
title: "Пример выкладки проекта с помощью debian-пакетов"
date: 2023-08-01T20:52:37.142+00:00
slug: longread-342-primer-vykladki-proekta-s-pomoshchyu-debian-paketov
summary: "Когда-то в Яндексе использовали интересный подход для деплоя сервисов — с помощью debian-пакетов. В этой статье я расскажу основную суть и покажу пример."
tags:
  - разработка
  - инфраструктура
tracker: "LONGREAD-11"
---

Когда-то в Яндексе использовали интересный подход для деплоя сервисов — с помощью debian-пакетов. В этой статье я расскажу основную суть и покажу пример.

**Debian-пакет** — архив со специальной структурой папок, в которые упакованы исходные файлы чего-либо (сайта, программы и/или прочего) и специальные файлы конфигурации, описывающие куда и каким образом будут копироваться эти исходные файлы на файловую систему.

У любого пакета имеется обязательная информация: 
* **ИМЯ ПАКЕТА** — для того, чтобы как-то отличать пакеты одного сервиса от пакетов другого сервиса;
* **ВЕРСИЯ ПАКЕТА** — чтобы как-то отличать разные пакеты одного проекта.

Для пакетов с одним именем существует одна особенность: при установке пакета более новой версии, пакет со старой версией будет полностью удален. Это означает, что нельзя установить две версии одного пакета.

{{< postimg src="image.webp" width="700" alt="image.png" >}}

## Создание debian-пакетов
Согласно [официальному гайду](https://www.debian.org/doc/manuals/debmake-doc/ch03.en.html#email-setup) необходимо указать дополнительные переменные окружения в `.bash_profile`:

```
export DEBFULLNAME="Name Surname"
export DEBEMAIL=login@yandex-team.ru
```

Все, что связано со сборкой пакетов, находится в служебной папке `debian`  в корне сервиса. 

Во внутренней документации в Яндексе я описывал алгоритм сборки debian-пакета на примере несуществующего сервиса `kukusik`. Не буду изменять традиции и в этой статье :)

Проект `kukusik` содержит как серверную часть ("динамику"), так и клиентскую ("статику"). Обе эти части должны быть выложены с помощью debian-пакетов.

У каждой команды в Яндексе был свой префикс для debian-пакетов, чтобы их легко можно было отличать в общем списке. В моей команде использовался префикс `yandex-maps-ui-`.

Создадим "скелет" для debian-пакета:
```
$ mkdir debian
$ dch --create --distribution unstable --package yandex-maps-ui-kukusik --newversion 1.0.0 "Initial version"
$ echo 10 > debian/compat
$ touch debian/control
$ touch debian/rules
$ chmod +x debian/rules
```

Было создано 4 файла:
* [changelog](https://www.debian.org/doc/manuals/maint-guide/dreq.en.html#changelog)
* [compat](https://www.debian.org/doc/manuals/maint-guide/dother.en.html#compat)
* [control](https://www.debian.org/doc/manuals/maint-guide/dreq.en.html#control)
* [rules](https://www.debian.org/doc/manuals/maint-guide/dreq.en.html#rules)

Файл `compat` отвечает за совместимость дебхелперов, и туда нужно записывать число 10.

Файл `changelog` содержит историю изменений пакета, его версию и прочую дополнительную информацию.

Наиболее интересны файлы `control` и `rules`. О них и пойдет речь в следующих разделах.

### control

В [control файле](http://www.debian.org/doc/manuals/maint-guide/dreq.ru.html#control) описывается служебная информация, которая будет использоваться при сборке и установке пакетов.

В `control` файле необходимо описать:
* управляющую информацию для пакета с исходным кодом (исходники сервиса) и бинарных пакетов (динамика и статика)
* список зависимостей, нужных для сборки
* мейнтейнера (ответственного за пакет)

Развертывание сервиса происходит тремя пакетами: один - для "динамики" и два - для "статики".

Почему для статики необходимо два пакета? Дело в том, что пакеты со статикой сразу размещаются на боевые сервера. Но если выложить пакет новой версии на боевой сервер с тем же именем, то предыдущая версия пакета будет удалена. Возникает вопрос: как установить две версии одного пакета одновременно, чтобы не сломать релиз, находящийся в продакшене, и развернуть новую версию в тестовом режиме? Было найдено хитрое решение, основанное на том, что при установке новой версии одного пакета, зависимости, указанные от этого пакета, устанавливаются, а при удалении - не уничтожаются.

Тогда было решено создать два пакета со статикой: [виртуальный](http://www.debian.org/doc/manuals/debian-faq/ch-pkg_basics.ru.html#s-virtual) (yandex-maps-ui-kukusik-static) и настоящий, в имени которого добавлялся номер версии для уникальности (yandex-maps-ui-kukusik-static-).

Т.е. для каждой новой версии статики создается абсолютно новый пакет, и он записывается в зависимости для виртуального пакета. Например, при сборке версии `1.0.0` мы получим два пакета со статикой: `yandex-maps-ui-kukusik-static=1.0.0`,  у которого будет прописана зависимость от пакета `yandex-maps-ui-kukusik-static-1-0-0=1.0.0`. Именно последний пакет и будет фактически устанавливаться на машинку.

{{< postimg src="175-image.webp" width="700" alt="image.png" >}}

{{< postimg src="176-image.webp" width="700" alt="image.png" >}}

Итоговый `control` файл будет выглядеть следующим образом:

```
Source: yandex-maps-ui-kukusik
Priority: optional
Build-Depends: cdbs
Maintainer: Kukusik <kukusik@kukusik.ru>

Package: yandex-maps-ui-kukusik
Priority: optional
Architecture: all
Description: WWW for kukusik

Package: yandex-maps-ui-kukusik-static-1-0-0
Priority: optional
Architecture: all
Description: Static for WWW for kukusik

Package: yandex-maps-ui-kukusik-static
Priority: optional
Depends: yandex-maps-ui-kukusik-static-1-0-0 (>= 1.0.0)
Architecture: all
Description: Depends on latest yandex-maps-ui-kukusik-static-
```

### rules

[rules](http://www.debian.org/doc/manuals/maint-guide/dreq.ru.html#rules) — специальный Makefile с инструкциями для сборки пакета.

Для сборки пакета обычно используется [CDBS](http://ru.wikipedia.org/wiki/CDBS) с набором хелперов и предустановленных переменных.

В Яндексе было написано два [debhelper](http://ru.wikipedia.org/wiki/Debhelper):
* `dh_versions` для замены строки `{{DEBIAN_VERSION}}` в указанных файлах или директориях
* `dh_environment` формирует postinstall-файл, который после установки пакета проставит симлинку`current`  в конфигах в зависимости от [окружения](https://t.me/tarmolov_work/139)

Чтобы не усложнять, я напишу упрощенную реализацию прямо в файле `rules`.

Таким образом `rules`  должен выглядеть примерно так:

```
#!/usr/bin/make -f

include /usr/share/cdbs/1/rules/buildvars.mk
include /usr/share/cdbs/1/rules/debhelper.mk

ENVIRONMENT=$(shell cat /etc/yandex/environment.type)

DEB_PACKAGE_DESTDIR=debian/$(DEB_SOURCE_PACKAGE)/usr/local/www/app/$(DEB_SOURCE_PACKAGE)
DEB_NGINX_CONFIG_DESTDIR=debian/$(DEB_SOURCE_PACKAGE)-nginx-config/etc/nginx/sites-available

STATIC_PACKAGE=$(if $(filter $(DEB_SOURCE_PACKAGE)-static-%,$(DEB_PACKAGES)),$(DEB_SOURCE_PACKAGE)-static-$(subst .,-,$(DEB_VERSION)))
DEB_STATIC_PACKAGE_DESTDIR=debian/$(STATIC_PACKAGE)/usr/local/www/static/$(subst yandex-maps-ui-,,$(DEB_SOURCE_PACKAGE))/$(DEB_VERSION)/

debian/control::
▸   sed -i 's!^\(Package: \).\+-static\-.*!\1$(STATIC_PACKAGE)!' $@
▸   sed -i 's!^\(Depends: \).\+-static\-.*!\1$(STATIC_PACKAGE) (>= $(DEB_VERSION))!' $@

build:
▸   ln -snf $(ENVIRONMENT) configs/current
▸   find configs -type f -exec sed -i 's/{{DEB_VERSION}}/$(DEB_VERSION)/g' {} \;
▸   npm i
▸   npm run build
▸   npm prune --production

install/$(DEB_SOURCE_PACKAGE)::
▸   mkdir -p $(DEB_PACKAGE_DESTDIR)
▸   cp -r node_modules configs server package.json $(DEB_PACKAGE_DESTDIR)

install/$(STATIC_PACKAGE)::
▸   mkdir -p $(DEB_STATIC_PACKAGE_DESTDIR)
▸   cp -r out $(DEB_STATIC_PACKAGE_DESTDIR)
```

В проекте `kukusik`  используются только две цели:
* `build` выполнится один раз для запуска сборки проекта;
* `install` служит для установки файлов в дерево файлов для каждого бинарного пакета из каталога debian.

См. также:
* [доступные цели в файле rules](http://www.debian.org/doc/manuals/maint-guide/dreq.ru.html#targets)
* [чем отличается `:` и `::` в названиях целей в файле rules](http://www.gnu.org/software/make/manual/html_node/Double_002dColon.html)

### Особенности пакета со статикой
В Яндексе также использовались файлы `postinst.in` и `postrm.in` для статического пакета. Первый из них выполняется после установки пакета (часто в нем прописывается установка различных симлинков), а второй — после удаления (т.е. когда начинает выполняться `postrm`, то пакет уже удален).

Все статические файлы во фронтенде подключаются с CDN по версионированному пути, например: `http://yastatic.net/kukusik/1.0.0/pages/index/_index.css` .

Однако, все картинки лежат в одной папке и не зависят от версии, например,
`http://yastatic.net/kukusik/_/SRaiqrtlCWzYa3hXDwJxk_zoHIY.svg` . Это нужно для того, чтобы при выкладке очередного релиза пользователи не загружали заново все картинки.

После установки нового пакета со статикой все новые картинки добавляются в общую кучу.

А при удалении пакета собираются картинки со всех установленных пакетов со статикой, этот список сравнивается с тем, что есть в общей куче, и удаляются неиспользуемые картинки. Тем самым папка `_`  всегда содержит актуальный список картинок, которые используются хотя бы в одном пакете со статикой.

Для простоты я не стал реализовывать этот механизм в своем примере. Но я открыт для [пулриквестов](https://github.com/tarmolov/yandex-maps-ui-kukusik/pulls) ;)

### Nginx-конфиг
Исторически мы используем nginx для проксирования запросов в само приложение.

Сборку отдельного пакета несложно добавить в текущую систему.

Создадим конфиг в `debian/nginx.conf`:
```
server {
    listen [::]:8081 ipv6only=off backlog=204;

    location / {
        proxy_pass http://127.0.0.1:8080/;
    }
}
```

В `control` файл нужно добавить несколько строк:
```
Package: yandex-maps-ui-kukusik-nginx-config
Architecture: all
Description: Nginx config for kukusik
```

В `rules` файл нужно добавить несколько строк:
```
install/$(DEB_SOURCE_PACKAGE)-nginx-config::
    mkdir -p $(DEB_NGINX_CONFIG_DESTDIR)
    cp debian/nginx.conf $(DEB_NGINX_CONFIG_DESTDIR)/$(DEB_SOURCE_PACKAGE).conf
```

Еще дополнительно настроить `postinst` и `postrm` для создания и удаления симлинки в `/etc/nginx/sites-enabled`.

### Запуск приложения
Для запуска приложений в Яндексе использовался [upstart](https://en.wikipedia.org/wiki/Upstart_(software)), но за это время появился специализированный менеджер процессов для nodejs — [pm2](https://pm2.keymetrics.io/).

Строка запуска выглядит следующим образом:
```
pm2 start /usr/local/www/app/yandex-maps-ui-kukusik/server/app.js
```

### Полный пример
Чтобы можно было попробовать сборку debian-пакетов самостоятельно, я создал [небольшой проект на гитхабе](https://github.com/tarmolov/yandex-maps-ui-kukusik). В нем используется все то, что я описывал в статье.

Вы сами можете убедиться, что это рабочий вариант для выкладки проектов ;)
