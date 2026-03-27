---
title: "Компонент secret в трекере"
date: 2023-03-07T09:38:52+00:00
slug: 203-komponent-secret-v-trekere
summary: "Иногда в трекере необходимо скрыть задачу от лишних глаз."
tags:
  - лайфхаки
  - безопасность
telegram: "https://t.me/tarmolov_work/104"
tracker: "BLOG-203"
---

{{< alert icon="brands/telegram" >}}
Оригинал опубликован в [Telegram](https://t.me/tarmolov_work/104)
{{< /alert >}}

![image.png](images/image.webp)

Иногда в [трекере](https://cloud.yandex.ru/services/tracker) необходимо скрыть задачу от лишних глаз.

Делюсь маленьким лайфхаком, упрощающим этот процесс:

1. Создайте компонент `secret` с [ограниченным доступом](https://cloud.yandex.ru/docs/tracker/manager/queue-access#access-components).
2. Рекомендую сразу выдавать доступ службе безопасности своей компании.

Если доступ к задаче нужно ограничить, то добавляете компонент `secret` - и доступ автоматически ограничится узким кругом лиц.