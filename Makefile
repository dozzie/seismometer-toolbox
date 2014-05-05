#!/usr/bin/make -f

.PHONY: default doc html tarball egg clean

default: tarball

doc: html

html:
	${MAKE} -C doc html

tarball:
	python setup.py sdist --formats=zip

egg:
	python setup.py bdist_egg

clean:
	python setup.py clean --all
	rm -rf dist
