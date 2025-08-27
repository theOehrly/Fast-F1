# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

VERSION ?= dev

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

show:
	@python -c "import webbrowser; webbrowser.open_new_tab('file://$(shell pwd)/_build/html/index.html')"

serve:
	@python -m http.server --directory $(shell pwd)/_build/html/

clean-gallery:
	@rm -rf $(shell pwd)/gen_modules/examples_gallery/*

version-build:
	@rm -rf $(shell pwd)/_build/html/tmp/
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "_build/tmp"
	@echo $(VERSION) > $(shell pwd)/_build/tmp/.version
	./setup_versioning.sh $(VERSION)


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
