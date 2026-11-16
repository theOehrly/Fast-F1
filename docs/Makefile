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

.PHONY: help Makefile show serve clean-gallery version-build record-data

show:
	@python -c "import webbrowser; webbrowser.open_new_tab('file://$(shell pwd)/_build/html/index.html')"

serve:
	@python -m http.server --directory $(shell pwd)/_build/html/

clean-gallery:
	@rm -rf $(shell pwd)/gen_modules/examples_gallery/*

# Re-record the frozen API responses in docs/data. Requires an IP address that
# is not blocked by the F1 API. The stage 2 cache and the previous build output
# must be gone, else most examples are never executed and nothing is recorded.
record-data:
	@rm -rf $(shell pwd)/../doc_cache
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@FASTF1_DOCS_CREATE_HTTP_CACHE=1 $(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

version-build:
	@rm -rf $(shell pwd)/_build/html/tmp/
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "_build/tmp"
	@echo $(VERSION) > $(shell pwd)/_build/tmp/.version
	./setup_versioning.sh


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
