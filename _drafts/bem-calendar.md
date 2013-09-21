---

layout: post
title:  "Simple BEM calendar"
date:   2013-09-15 20:31:12
categories: blog

---

First of all, a little preface. A couple of weeks ago I have got to know about Frontend Developer School run by [HeadHunter](http://hh.ru/locale.do?language=EN). They suggested you to make a simple calendar as an entering assigment. It seemed a quite interesting issue for me and I decided to solve it using new [bem-core](https://github.com/bem/bem-core/) library.

In this article you will see several parts:

  * **Design part** tells you how I designed my mini application.
  * **Tools** teach you which kind of tools makes development handy and cozy.
  * **Development**.
  * **Testing** shows you how I tested my project and made it stable.
  * **Continuous intergration** is last one and it tells you something about automatization.

**Note.** It is a long article. If you do not want to read a lot please go to [github](https://github.com/tarmolov/bem-calendar#bem-calendar-) for short version :)

**Note.** If you are not familiar with BEM methodology I will recommend to read about it at [bem.info](http://bem.info/).

Let us start with Design part.

### Design part
[BEM methodology](http://bem.info/) teachs you that a first step of building web site is to mark out page blocks. In my case it is a easy peasy issue because of a simple page.

[![Calendar blocks](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_blocks/image_blocks_all.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_blocks/image_blocks_all.png)

But the most major blocks are only four:

  * Toolbar with a couple of buttons.
  * Search with search input and icon.
  * Calendar navigation.
  * And calendar itself.

I marked blocks at a screenshot bellow:

[![Calendar blocks](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_blocks/image_blocks_main.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_blocks/image_blocks_main.png)

Next step is more interesting. How to connect these blocks and to make application work?

It seems that I need a small but a good architecture for the calendar.

I like an approach presented by Nicholas C. Zakas and called Scalable JavaScript Application Architecture. If you are not familiar with this approach you can [watch video](http://bem.github.io/bem-bl/sets/common-desktop/i-bem/i-bem.en.html) or [read slides](http://bem.github.io/bem-bl/sets/common-desktop/i-bem/i-bem.en.html). The major idea is to divide responsibility and business logic among several layers of an application. Each layer has knowledge only about adjacent layers.

[![Level of abstractions](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_design/image_design_zakas.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_design/image_design_zakas.png)

In my case this paradigm does not work completely because of bem-core.

In [the official page](https://github.com/bem/bem-core/) we can read follow definition:
> bem-core is a base library for web interface development. It provides the minimal stack for coding client-side JavaScript and templating.

bem-core uses [specific module system](https://github.com/ymaps/modules) which still has not name; so I called it just YMaps Module System (YMS). It solves problems such as asynchronous require and provide which cannot provide AMD and CommonJS approaches. It is a pretty good modules system and I strongly recommend you to try it in your new project.

Also bem-core provides a lot of useful modules (and the module system itself) but I has included this library for the i-bem. It is a helper for creating BEM blocks in declarative way. I am ashamed to admit that we have not good documentation for i-bem in English (but I hope situation will change). I will show you an example later.

So why cannot I implement this paradigm completely? Because bem-core uses jQuery which penetrated into all parts of i-bem. As a result you have to use jQuery in your BEM blocks and blocks know about base library.

My architecture overview is presented in diagramm bellow:
[![Architecture overview](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_design/image_design_tarmolov.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_design/image_design_tarmolov.png)

You can see that BEM is not displayed at the diagramm. My architecture should not depend on BEM or another methadology.

There are a few differences:

  * Every layer could know about base library.
  * Component manager is responsible for starting and stopping components.
  * Modules called components because I have already have modules provided by YMS and I do not want to have business with name conflict.

For storing application data I use a simple active model which could be accessible through the sandbox, too. However, components do not know where the model comes from.

Components work as controllers in my application.More details you can see in class diagram:

[![Class diagram](https://raw.github.com/tarmolov/bem-calendar/master/doc/uml/_class/uml_class_main.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/uml/_class/uml_class_main.png)

I have only four visual components:

  * Calendar.
  * Navigation.
  * Search.
  * Toolbar.

An each component represents itself using BEM block with the same name. When a component has been started, it creates BEM block as a View-Controller and puts it DOM node which has been gotten through Sandbox. Also I want to emphasize that components are very simple [mediators](http://en.wikipedia.org/wiki/Mediator_pattern). The majority of code is concentrated in BEM blocks.

And how application start would look like:

[![Application start](https://raw.github.com/tarmolov/bem-calendar/master/doc/uml/_sequence/uml_sequence_application-start.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/uml/_sequence/uml_sequence_application-start.png)

It looks very simple and it works very simple ;)

I wanted to achieve the stable core of my application; therefore, I had defined a couple of interfaces:

  * [ISandbox](https://github.com/tarmolov/bem-calendar/blob/master/blocks/interface/i-sandbox.js).
  * [IComponent](https://github.com/tarmolov/bem-calendar/blob/master/blocks/interface/i-component.js).
  * [IBEMView](https://github.com/tarmolov/bem-calendar/blob/master/blocks/interface/i-bemview.js).

There are boundary elements of my application. Sandbox connects application and components. Components connect with BEM blocks which implement IBEMView interface.

### Tools

When you use BEM your code is divided into great number of blocks. For production all files should be concatenated and minified. Of course you can do it manually but it is hell and usually we have been using a special tools for this issue.

At first, it was a Make-platform. Then [bem-tools](https://github.com/bem/bem-tools) was created. And then enb came.

[ENB](http://enb-make.info/) is a powerful and fast builder. In development mode you event do not notice that your fuiles has been built. It works just amazingly!

Also enb has a perfect documentation (at this moment only Russian version available), many-many technologies, and easy way to create new ones. New versions with fixed bugs and improvements are published often. I strongly recommend you to use this builder for your bem projects.

Moreover, enb makes it possible to get rid of dependencies for javascript modules. Enb can read javascript declarations and pick out dependencies from them. As a result I have added only 7 files with dependencies!

Next two tools are about validation javascript code: [jshint-groups](https://github.com/ikokostya/jshint-groups) and [jscs](https://github.com/mdevils/node-jscs).

First of them is [jshint](http://jshint.com/) wrapper. It adds possibility to create different rules for cheking files with jshint. There are tests, templates, client, and server javascript in your project. Now you can write separate and suitable jshint rules for all of them.

jscs is javascript codestyle checker. Make sure that your code is written in one codestyle! It has flexible config with a lot of predefined rules. If you do not find necessary rules you always [can add new ones](https://github.com/mdevils/node-jscs/blob/master/CONTRIBUTION.md).

The last one is [csscomb](https://github.com/csscomb/csscomb.js). This tool formats your css code. I love when css rules formatted with the same order and divided in groups. Csscomb could support your css coding style automatically if you want.

So enb, jshint-groups, jscs, ands csscomb. This is a bunch of great tools and I advise you to use them in everyday development.

### Development

BEM claims that you should create absolute independent blocks as much as possible. In css blocks should know only about their elements and they have not any knowledge about possible nested blocks. When you want to change style of nested blocks use mixins.

For example, see bemjson for search block

```
{
    block: 'search',
    content: [
        {
            block: 'icon',
            mix: [
                {block: 'search', elem: 'icon'}
            ],
            mods: {type: 'loupe'}
        },
        {
            block: 'input',
            mix: [
                {block: 'search', elem: 'input'}
            ]
        }
    ]
}
```

I mixed elements of search blocks to nested icons and input blocks. It makes it possible to write CSS for position of icon block, for instance.

```
.search__icon
{
    position: absolute;
    top: 50%;
    left: -20px;

    margin-top: -6px;
}
```

If I will decide to change icon block to megaicon block, I do not need to change styles in search block. Cool, hah?

Possible drawback is conflict styles of nested block and mixin. But I can stand it and control it. It is some kind of fee for such magic as mixins.

In javascript i-bem provides methods like findBlockInside/findBlockOn for finding nested blocks. It also provides method findBlockOutside but this method breaks the idea of independent blocks. Do not use this method at all!

All javascript modules were wrapped busing YMS. For example,
```
modules.define('i-bem__dom', function (provide, DOM) {

    DOM.decl('label', {

        setText: function (text) {
            this.domElem.text(text);
        },

        getText: function () {
            return this.domElem.text();
        }

    });

    provide(DOM);

});
```

However, declartion for navigation looks
```
modules.define('search', [/** deps **/], function () {

    provide(DOM.decl('search', {
        // ...
    }));

});
```

Please pay attention to module name. In the first case it is ```i-bem__dom``` but actually it is declared ```label```. In the second case I declared the modules with "right" name. Why did I declare modules with two different ways?

### Testing

### Continuous integration (CI)

[CI](http://en.wikipedia.org/wiki/Continuous_integration) is a good way to be calm about your project. At work I usually use a [TeamCity](http://www.jetbrains.com/teamcity/) by JetBrains which is perfectly suitable for our work issues. Teamcity helps to automate everything in our development process and does it well. Unfortunatelly our teamcity server is not opened for everyone. Moreover Teamcity is not free and you should own a server for setting it up

To be honest I did not want to buy server for this; so, I chose [Travis](http://travis-ci.org/) which is perfectly suitable for projects hosted on github.

Many developers have heard about CI because it is in a fashion but never used it. Why? Because it is so complex to set up? Or only serious guys could use it? Probably Travis is the easiest CI tool for set up.

You have to do only three steps:

  1. Sign in in [Travis CI](http://travis-ci.org/) and activate GitHub service Hook for your project.
  2. Add .travis.yaml file to your repository. For example, it could look like
  3. ```git push```

Travis CI config is simple. You should specify only language and version of nodejs.

```
language: node_js
node_js:
- 0.8
```

This configuration is sufficient for linting your code and running unit tests!

But I wanted more. My wish was regenerate my demo after each successful build when all tests has been passed. I quickly googled a [blog post](http://sleepycoders.blogspot.ru/2013/03/sharing-travis-ci-generated-files.html) with solution.

In a nutshell, you should teach Travis to authenticate to your repository with push permission.

  1. [Create a github access token](https://help.github.com/articles/creating-an-access-token-for-command-line-use).
  2. Encrypt your token and put it in travis config because without encoding everybody can use your token.

```
gem install travis
travis encrypt -r <user>/<repository> GH_TOKEN=<token> --add env.global
```

After that travis can clone repository with your project and push some changes to it. So I wrote a script [```update-gh-pages.sh```](https://github.com/tarmolov/bem-calendar/blob/master/update-gh-pages.sh) and appended a new directive to travis config:

```
after_success: ./update-gh-pages.sh
```

Push and it works like a magic.
