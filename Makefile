#!/usr/bin/make -f

SPHINX_DOCTREE = doc/doctrees
SPHINX_SOURCE = doc
SPHINX_OUTPUT = doc/html

.PHONY: default build doc html tarball egg clean

default: tarball

build:
	python setup.py build

install:
	mkdir -p $(DESTDIR)/etc/seismometer
	install -m 644 examples/daemonshepherd.logging $(DESTDIR)/etc/seismometer/daemonshepherd.logging.example
	install -m 644 examples/daemonshepherd.yaml    $(DESTDIR)/etc/seismometer/daemonshepherd.yaml.example
	install -m 644 examples/messenger.logging      $(DESTDIR)/etc/seismometer/messenger.logging.example
	install -m 644 examples/messenger.tags         $(DESTDIR)/etc/seismometer/messenger.tags.example
	install -m 644 examples/dumbprobe.logging      $(DESTDIR)/etc/seismometer/dumbprobe.logging.example
	install -m 644 examples/dumbprobe.py           $(DESTDIR)/etc/seismometer/dumbprobe.py.example
	python setup.py install --prefix=/usr --exec-prefix=/usr $(if $(DESTDIR),--root=$(DESTDIR))

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

# file used by debian/rules to override $(VERSION) variable (in case of
# building from source package instead of from git repository)
.PHONY: version
version:
	git describe --long --dirty --abbrev=10 --tags --match 'v[0-9]*' > $@
