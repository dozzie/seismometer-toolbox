#!/usr/bin/make -f

SPHINX_DOCTREE = doc/doctrees
SPHINX_SOURCE = doc
SPHINX_OUTPUT = doc/html

.PHONY: default doc html tarball egg clean

default: tarball

doc: html

html:
	sphinx-build -b html -d $(SPHINX_DOCTREE) $(SPHINX_SOURCE) $(SPHINX_OUTPUT)

tarball:
	python setup.py sdist --formats=zip

egg:
	python setup.py bdist_egg

clean:
	python setup.py clean --all
	rm -rf dist
	rm -rf $(SPHINX_DOCTREE) $(SPHINX_OUTPUT)
