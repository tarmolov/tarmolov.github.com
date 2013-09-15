---

layout: post
title:  "How to use bem-core"
date:   2013-09-15 20:31:12
categories: blog

---

###Continuous integration (CI)
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
