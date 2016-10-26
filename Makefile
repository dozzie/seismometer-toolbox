#!/usr/bin/make -f

SPHINX_DOCTREE = doc/doctrees
SPHINX_SOURCE = doc
SPHINX_HTML = doc/html
SPHINX_MANPAGES = doc/man

.PHONY: default doc html tarball egg clean

default: tarball

doc: html man

html:
	sphinx-build -b html -d $(SPHINX_DOCTREE) $(SPHINX_SOURCE) $(SPHINX_HTML)

man:
	sphinx-build -b man -d $(SPHINX_DOCTREE) $(SPHINX_SOURCE) $(SPHINX_MANPAGES)
	doc/bin/postprocess-manpages $(SPHINX_MANPAGES)/*.[1-8]

tarball:
	python setup.py sdist --formats=zip

egg:
	python setup.py bdist_egg

clean:
	python setup.py clean --all
	rm -rf dist
	rm -rf $(SPHINX_DOCTREE) $(SPHINX_HTML) $(SPHINX_MANPAGES)
