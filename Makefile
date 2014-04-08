#!/usr/bin/make -f

.PHONY: default tarball egg clean

default: tarball

tarball:
	python setup.py sdist --formats=zip

egg:
	python setup.py bdist_egg

clean:
	python setup.py clean --all
	rm -rf dist
