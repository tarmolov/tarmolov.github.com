all:
	@jekyll server --watch

deploy:
	@git stash
	@cp _site/{index.css,rss.xml} .
	@git add .
	@git commit --amend -C HEAD
	@git stash apply
	@git push -f origin master

clean:
	@rm -rf _site

.PHONY: all deploy clean
