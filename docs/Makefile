# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD  ?= sphinx-build
SOURCEDIR    = .
BUILDDIR     = _build

# Language settings
LANGUAGES    = de en
POT_DIR      = locales

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile clean-all install-deps

# Install Sphinx and dependencies
install-deps:
	pip install sphinx sphinx-intl sphinx-autodoc-typehints sphinx-rtd-theme myst-parser sphinx-copybutton

# Clean everything including translations
clean-all:
	rm -rf $(BUILDDIR)
	rm -rf $(POT_DIR)

# Generate .pot files for translation
gettext:
	@$(SPHINXBUILD) -b gettext $(SOURCEDIR) $(POT_DIR)
	@echo "Generated .pot files in $(POT_DIR)/"

# Update translation files
update-translations: gettext
	@for lang in $(LANGUAGES); do \
		if [ "$$lang" != "de" ]; then \
			sphinx-intl update -p $(POT_DIR) -l $$lang; \
		fi \
	done
	@echo "Updated translation files for languages: $(LANGUAGES)"

# Build German documentation (default)
html-de:
	@$(SPHINXBUILD) -b html -D language=de $(SOURCEDIR) $(BUILDDIR)/html/de $(SPHINXOPTS)
	@echo "German documentation built in $(BUILDDIR)/html/de/"

# Build English documentation
html-en:
	@$(SPHINXBUILD) -b html -D language=en $(SOURCEDIR) $(BUILDDIR)/html/en $(SPHINXOPTS)
	@echo "English documentation built in $(BUILDDIR)/html/en/"

# Build all languages
html-all: html-de html-en
	@echo "All language versions built successfully!"

# Create index.html that redirects to German version
html-index:
	@mkdir -p $(BUILDDIR)/html
	@echo '<!DOCTYPE html>' > $(BUILDDIR)/html/index.html
	@echo '<html><head><meta charset="utf-8">' >> $(BUILDDIR)/html/index.html
	@echo '<meta http-equiv="refresh" content="0; url=de/">' >> $(BUILDDIR)/html/index.html
	@echo '<title>MSFW Documentation</title></head>' >> $(BUILDDIR)/html/index.html
	@echo '<body><p>Redirecting to <a href="de/">German documentation</a>...</p>' >> $(BUILDDIR)/html/index.html
	@echo '<p><a href="en/">English documentation</a></p></body></html>' >> $(BUILDDIR)/html/index.html
	@echo "Created redirect index.html"

# Build complete documentation with all languages
html: html-all html-index
	@echo "Complete multilingual documentation built!"
	@echo "German: $(BUILDDIR)/html/de/"
	@echo "English: $(BUILDDIR)/html/en/"

# Serve documentation locally
serve:
	@cd $(BUILDDIR)/html && python -m http.server 8080
	@echo "Documentation served at http://localhost:8080"

# Build documentation for development (with auto-rebuild)
dev:
	@sphinx-autobuild -b html -D language=de $(SOURCEDIR) $(BUILDDIR)/html/de $(SPHINXOPTS) --host 0.0.0.0 --port 8000

# Lint documentation
lint:
	@sphinx-build -b linkcheck -D language=de $(SOURCEDIR) $(BUILDDIR)/linkcheck $(SPHINXOPTS)
	@echo "Link check completed"

# Generate API documentation
autodoc:
	@sphinx-apidoc -o api ../msfw ../msfw/tests
	@echo "API documentation generated"

# Build PDF documentation (requires LaTeX)
pdf-de:
	@$(SPHINXBUILD) -b latex -D language=de $(SOURCEDIR) $(BUILDDIR)/latex/de $(SPHINXOPTS)
	@cd $(BUILDDIR)/latex/de && make
	@echo "German PDF built in $(BUILDDIR)/latex/de/"

pdf-en:
	@$(SPHINXBUILD) -b latex -D language=en $(SOURCEDIR) $(BUILDDIR)/latex/en $(SPHINXOPTS)
	@cd $(BUILDDIR)/latex/en && make
	@echo "English PDF built in $(BUILDDIR)/latex/en/"

pdf: pdf-de pdf-en
	@echo "PDF documentation built for all languages"

# Build EPUB documentation
epub-de:
	@$(SPHINXBUILD) -b epub -D language=de $(SOURCEDIR) $(BUILDDIR)/epub/de $(SPHINXOPTS)
	@echo "German EPUB built in $(BUILDDIR)/epub/de/"

epub-en:
	@$(SPHINXBUILD) -b epub -D language=en $(SOURCEDIR) $(BUILDDIR)/epub/en $(SPHINXOPTS)
	@echo "English EPUB built in $(BUILDDIR)/epub/en/"

epub: epub-de epub-en
	@echo "EPUB documentation built for all languages"

# Deploy to GitHub Pages
deploy:
	@if [ ! -d "$(BUILDDIR)/html" ]; then \
		echo "Building documentation first..."; \
		make html; \
	fi
	@echo "Deploying to GitHub Pages..."
	@cd $(BUILDDIR)/html && \
		git init && \
		git add . && \
		git commit -m "Deploy documentation" && \
		git push -f git@github.com:Scharxi/msfw.git main:gh-pages
	@echo "Documentation deployed to GitHub Pages"

# Show documentation statistics
stats:
	@echo "Documentation Statistics:"
	@echo "========================="
	@find . -name "*.md" -not -path "./_build/*" | wc -l | xargs echo "Markdown files:"
	@find . -name "*.rst" -not -path "./_build/*" | wc -l | xargs echo "reStructuredText files:"
	@wc -l `find . -name "*.md" -not -path "./_build/*"` | tail -1 | xargs echo "Total lines in .md files:"

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O) 