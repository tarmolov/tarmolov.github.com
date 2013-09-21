---

layout: post
title:  "Simple BEM calendar"
date:   2013-09-22 19:31:12
categories: blog

---

First of all, a little preface. A couple of weeks ago I got to know about Frontend Developer School run by [HeadHunter](http://hh.ru/locale.do?language=EN). The entering assigment was to make a simple calendar. It seemed a quite interesting issue for me and I decided to solve it using new [bem-core](https://github.com/bem/bem-core/) library.

This article is divided into several parts:

  * **Design** tells you how I designed my mini application.
  * **Tools** teach you which kind of tools makes development handy and cozy.
  * In **Development** I tell you about established solutions and problems.
  * **Testing** shows you how I tested my project and made it stable.
  * **Continuous intergration** is last one and it tells you something about automatization.

**Note.** It is a long article. If you do not want to read a lot please go to project page on [github](https://github.com/tarmolov/bem-calendar#bem-calendar-) for short version :)

**Note.** If you are not familiar with BEM methodology and want to learn more [bem.info](http://bem.info/) is the best choice.

Let us start with Design part.

### Design

[BEM methodology](http://bem.info/) teachs you that a first step of building web site is to mark out page blocks. In my case it is a easy peasy issue because of a simple page.

[![Calendar blocks](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_blocks/image_blocks_all.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_blocks/image_blocks_all.png)

But I have only four major blocks:

  * Toolbar with a couple of buttons.
  * Search with input and icon.
  * Calendar navigation.
  * And calendar itself.

I marked blocks at a screenshot bellow:

[![Calendar blocks](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_blocks/image_blocks_main.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_blocks/image_blocks_main.png)

Next step is much more interesting. How to connect these blocks and to make application work?

It seems that I need a small but robust architecture for the calendar.

I liked an approach presented by Nicholas C. Zakas and called [Scalable JavaScript Application Architecture](http://www.youtube.com/watch?v=7BGvy-S-Iag). The major idea is to divide responsibility and business logic among several layers of an application. Each layer has knowledge only about adjacent layers.

[![Level of abstractions](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_design/image_design_zakas.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_design/image_design_zakas.png)

In my case this paradigm does not work completely because of bem-core. I will explain the reason lately but now a couple of words about the library.

In [the official page](https://github.com/bem/bem-core/) we can read follow definition:
> bem-core is a base library for web interface development. It provides the minimal stack for coding client-side JavaScript and templating.

bem-core uses [special module system](https://github.com/ymaps/modules) which still has not name; so I called it just YMaps Module System (YMS). It solves problems such as asynchronous require and provide which are absent in AMD and CommonJS. It is a pretty good module system and I strongly recommend you to try it in your new project.

Also bem-core provides a lots of useful modules (and the module system itself) but I has included this library for the [i-bem](http://bem.info/articles/bem-js-main-terms/). It is a helper for creating BEM blocks in declarative way.

So why cannot I implement this paradigm completely? Now I can do an answer. Because bem-core uses jQuery which penetrated into all parts of i-bem. As a result you have to use jQuery in your BEM blocks and blocks know about base library.

My architecture overview is presented in a diagramm bellow:
[![Architecture overview](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_design/image_design_tarmolov.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/image/_design/image_design_tarmolov.png)

You can see that BEM is not displayed at the diagramm. In my opinion base architecture should not depend on BEM or another methadology.

There are a few differences:

  * Every layer could know about base library: everything needs jQuery :)
  * Component manager is responsible for starting and stopping components.
  * Modules called components because I already have modules from YMS (conflict names).

For storing an application data I use a simple active model which could be accessible through the sandbox, too. However, components do not know where the model comes from. It is important.

I have only four visual components:

  * Calendar
  * Navigation
  * Search
  * Toolbar

And one is non-visual for synching my application with localStorage.

Each component represents itself using BEM block with the same name (but it is not necessary requirement). When a component has been started, it creates BEM block as a View-Controller and puts it into DOM node which has been gotten from Sandbox.

In the calendar components work as controllers which can communicate only through the model i.e. indirectly. Also I want to emphasize that components are very simple [mediators](http://en.wikipedia.org/wiki/Mediator_pattern). The majority of code is concentrated in BEM blocks.

More details you can see in class diagram:

[![Class diagram](https://raw.github.com/tarmolov/bem-calendar/master/doc/uml/_class/uml_class_main.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/uml/_class/uml_class_main.png)

Application start is obvious and straitghforward:

[![Application start](https://raw.github.com/tarmolov/bem-calendar/master/doc/uml/_sequence/uml_sequence_application-start.png)](https://raw.github.com/tarmolov/bem-calendar/master/doc/uml/_sequence/uml_sequence_application-start.png)

It looks very simple and it works very simple ;)

I wanted to achieve the stable core of my application; therefore, I had defined interfaces for major classes:

  * [ISandbox](https://github.com/tarmolov/bem-calendar/blob/master/blocks/interface/i-sandbox.js)
  * [IComponent](https://github.com/tarmolov/bem-calendar/blob/master/blocks/interface/i-component.js)
  * [IBEMView](https://github.com/tarmolov/bem-calendar/blob/master/blocks/interface/i-bemview.js)

There are boundary elements of my application. Sandbox connects application and components. Components connect with BEM blocks which implement IBEMView interface.

Using interfaces is always increase stability of your application.

### Tools

When you use BEM your code is divided into great number of blocks. Then files will be concatenated and minified. Of course we can do it manually but usually we have been using special tools for this issue.

At first, it was a make-platform. Then [bem-tools](https://github.com/bem/bem-tools) was created. And then enb came.

[enb](http://enb-make.info/) is a powerful and fast builder. In development mode you even do not notice that your fuiles has been built. It works just amazingly!

Also enb has a perfect documentation (at this moment only Russian version available), many-many technologies, and easy way to create new ones. New versions with fixed bugs and improvements are published very often. I strongly recommend you to use this builder for your BEM projects.

Moreover, enb makes it possible to get rid of dependencies for javascript modules because it can read them from YMS declarations. As a result I have added only 7 files with dependencies!

By default bem-core recommends you to use [BEMHTML](http://bem.info/articles/bemhtml-intro/) template engine. However, I recommend to use [bh](github.com/enb-make/bh) template engine. It much faster than BEMHTML and works without compilation. Also it is small and easy to use. You just write commonjs modules:

```
module.exports = function (bh) {
    bh.match('button', function (ctx) {
        ctx.tag('button');
    });
};
```

Next two tools are about validation javascript code: [jshint-groups](https://github.com/ikokostya/jshint-groups) and [jscs](https://github.com/mdevils/node-jscs).

First of them is a [jshint](http://jshint.com/) wrapper. It adds possibility to add different rules for cheking files with jshint. There are tests, templates, client, and server javascript in your project. Now you can write separate and suitable jshint rules for all of them. It is a flexibale way to lint your code.

jscs is a javascript codestyle checker. Make sure that your code is written in one codestyle! It provides a lots of predefined rules. If you do not find necessary rules you  [can add new ones](https://github.com/mdevils/node-jscs/blob/master/CONTRIBUTION.md).

The last one is [csscomb](https://github.com/csscomb/csscomb.js). This tool formats your CSS code. I love when CSS rules formatted with the same order and divided into groups. In my opinion such nice-looking code easy to read and maintain.

So enb, jshint-groups, jscs, ands csscomb. This is a bunch of great tools and I advise you to use them in everyday development.

### Development

BEM claims that you should create absolute independent blocks as much as possible. In CSS blocks should know only about their elements and they have not any knowledge about possible nested blocks. When you want to change style of nested blocks use mixins.

For example, see bemjson for search block

```
{
    block: 'search',
    content: [
        {
            block: 'icon',
            mix: [
                {
                    block: 'search',
                    elem: 'icon'
                }
            ],
            mods: {type: 'loupe'}
        },
        {
            block: 'input',
            mix: [
                {
                    block: 'search',
                    elem: 'input'
                }
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

Possible drawback is a conflict styles of nested block and mixin. But I accept this shorcoming. It is some kind of fee for such magic as mixins.

In javascript i-bem provides methods like findBlockInside/findBlockOn for finding nested blocks. It also provides method findBlockOutside but this method breaks the idea of independent blocks. Do not use this method at all!

All javascript modules were wrapped using YMS. For example,

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

Definition depends on how you use the module in your application.

Search module has been created manually in search component; so, the code would be executed during application initilization. Label on the other hand is used latently in form_type_event dureing generating bemjson for showing form. This block should be initialized by execting ```DOM.init``` and ```i-bem``` can init only blocks declared in special way, i.e. as ```i-bem__dom``` module.

Be careful when you declare your modules.

### Testing

When you work in a big company such as [Yandex](http://yandex.com/) your application is always accurately checked by testing team.

I am proud to say that we have a unbelievable testing team! They are really incredible. They can find bugs which reproduced very-very tricky way (and sometimes I even litle bit hate them). Anyway after such careful check you can calmly publish an application in production.

However, this project is not a part of my job and I have not great testers to verify my application. Therefore I undertook three steps to create a stable application.

First step is a linting code with jshint and jscs. I have already told you about them in Tools part. After this step I have consistent code. Good begining.

Unit testing is a next step. In my opinion tests is an important part of your code, i.e. code is not only code but tests, too. Using phantomjs to run tests in console or automatically after each commit speed up development and refactoring.

Honestly, I usually write tests only after I have completed structure (backbone) of an application. I do not use TDD approach. Anyway without unit tests I cannot guarantee that my application works properly :)

I think it does not matter what kind of framework you choose for unit testing. For instance, I used [mocha](http://visionmedia.github.io/mocha/) + [chai](http://chaijs.com/) + [sinon](http://sinonjs.org/) for BEM calendar. Unit testing cannot completely save the day, though. They do not test the application in different browsers.

I have a mac and can test my calendar only in couple browsers and on one platform. First idea was to download virtual machines from [modern.ie](http://www.modern.ie/). But I have not much time to test the calendar in all virtual machines.

So my choice is [BrowserStack](http://www.browserstack.com/) with a wide range of browser and platforms. Firstly, this service runs your site in a lots of  browsers (25 in free version) and [creates screnshot for each of them](http://www.browserstack.com/screenshots/18d918bb9bb188f9df08b436be34835ad01735f7). If you notice an error in a screenshot you can run virtual machine in browser and explore its reason in detail.

I am very lazy and I do not want to do extra actions for testing. So I created a special page [calendar-test](http://tarmolov.github.io/bem-calendar/pages/calendar-test/calendar-test.html) where my testing script adds event and opens popups. Now I can [quickly verify work of my application](http://www.browserstack.com/screenshots/0742d8374fe1836f15e8774719e465a2adade766).

Linting code, unit testing, and browserStack help you to make an application very stable. Use them wise.

### Continuous integration (CI)

[CI](http://en.wikipedia.org/wiki/Continuous_integration) is a good way to be calm about your project. At work I usually use [TeamCity](http://www.jetbrains.com/teamcity/) by JetBrains which is perfectly suitable for our work issues. Teamcity helps to automate everything in our development process and does it well. Unfortunatelly our teamcity server is not opened for everyone. Moreover Teamcity is not free and you should own a server for setting it up.

To be honest I did not want to buy server for this project; so, I chose [Travis](http://travis-ci.org/) which is perfectly suitable for projects hosted on github.

Many developers have heard about CI because it is in a fashion but never used it. Why? Because it is so complex to set up? Or only serious guys could use it? It is a myth. Try Travis. Probably it is the easiest CI tool for set up.

You have to do only three steps:

  1. Sign in in [Travis CI](http://travis-ci.org/) and activate GitHub service Hook for your project.
  2. Add .travis.yaml file to your repository.
  3. ```git push```

Travis CI config is simple. You should specify only language and version of nodejs.

```
language: node_js
node_js:
- 0.8
```

This configuration is sufficient for linting your code and running unit tests! Do not forget to add ```scripts``` section in your package.json.

But I wanted more. My wish was regenerate my demo after each successful build when all tests has been passed. I quickly googled a [blog post](http://sleepycoders.blogspot.ru/2013/03/sharing-travis-ci-generated-files.html) with solution.

In a nutshell, you should teach Travis to authenticate to your repository with push permission.

  1. [Create a github access token](https://help.github.com/articles/creating-an-access-token-for-command-line-use).
  2. Encrypt your token and put it in travis config because without encoding everybody can use your token (and broke your repo).

```
gem install travis
travis encrypt -r <user>/<repository> GH_TOKEN=<token> --add env.global
```

After that travis can clone repository with your project and push some changes to it. So I wrote a script [```update-gh-pages.sh```](https://github.com/tarmolov/bem-calendar/blob/master/update-gh-pages.sh) and appended a new directive to travis config:

```
after_success: ./update-gh-pages.sh
```

Then push and it works like a magic.

### Conclusion

BEM calendar is a very simple appliction but this article is not about creating calendars. My goal is to show you principles of good development:

  * Develope desing of an application carefully and lay the groundwork for future possible features.
  * Use tools which help to write more accurate and stable code.
  * Test your code not only with unit tests but add crossbrowser tests, too.
  * Automate everythin you can do.

I hope this article teachs you something interesting.

And of course thank you to read to the end ;)
