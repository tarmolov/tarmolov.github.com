all:
	@jekyll server --watch

deploy:
	@cp _site/{index.css,index.ie.css,rss.xml} .
	@git add index.css index.ie.css rss.xml
	@git commit --amend -C HEAD
	@git push -f origin master

clean:
	@rm -rf _site

.PHONY: all deploy clean
