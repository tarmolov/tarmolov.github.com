all:
	@jekyll server --watch

deploy:
	@git stash
	@cp _site/index.css .
	@git add .
	@git commit --amend -C HEAD
	@git stash apply
	@git push -f origin master

dev:
	@jekyll server --watch --drafts


clean:
	@rm -rf _site

.PHONY: all deploy clean
