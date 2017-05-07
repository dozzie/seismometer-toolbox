#!/usr/bin/make -f

SPHINX_DOCTREE = doc/doctrees
SPHINX_SOURCE = doc
SPHINX_HTML = doc/html
SPHINX_MANPAGES = doc/man

.PHONY: default build doc html tarball egg clean

default: tarball

build:
	python setup.py build

install: build doc
	mkdir -p $(DESTDIR)/etc/seismometer
	mkdir -p $(DESTDIR)/usr/share/doc/seismometer-toolbox
	mkdir -p $(DESTDIR)/usr/share/man
	install -m 644 examples/daemonshepherd.logging $(DESTDIR)/etc/seismometer/daemonshepherd.logging.example
	install -m 644 examples/daemonshepherd.yaml    $(DESTDIR)/etc/seismometer/daemonshepherd.yaml.example
	install -m 644 examples/messenger.logging      $(DESTDIR)/etc/seismometer/messenger.logging.example
	install -m 644 examples/messenger.tags         $(DESTDIR)/etc/seismometer/messenger.tags.example
	install -m 644 examples/dumbprobe.logging      $(DESTDIR)/etc/seismometer/dumbprobe.logging.example
	install -m 644 examples/dumbprobe.py           $(DESTDIR)/etc/seismometer/dumbprobe.py.example
	python setup.py install --prefix=/usr --exec-prefix=/usr $(if $(DESTDIR),--root=$(DESTDIR))
	mkdir -p $(DESTDIR)/usr/share/doc/seismometer-toolbox/html
	cp -R doc/html/*.html doc/html/*.js doc/html/*/ $(DESTDIR)/usr/share/doc/seismometer-toolbox/html
	install -m 644 -D doc/man/seismometer-message.7 $(DESTDIR)/usr/share/man/man7/seismometer-message.7
	install -m 644 -D doc/man/daemonshepherd.8 $(DESTDIR)/usr/share/man/man8/daemonshepherd.8
	install -m 644 -D doc/man/dumb-probe.8     $(DESTDIR)/usr/share/man/man8/dumb-probe.8
	install -m 644 -D doc/man/hailerter.8      $(DESTDIR)/usr/share/man/man8/hailerter.8
	install -m 644 -D doc/man/messenger.8      $(DESTDIR)/usr/share/man/man8/messenger.8

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
