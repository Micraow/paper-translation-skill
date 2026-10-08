SHELL := /bin/bash
.DEFAULT_GOAL := all

MAIN ?= main.tex
BUILD_DIR ?= build
BIB_MODE ?= native
BASE_PDF := $(BUILD_DIR)/main.pdf
FINAL_PDF := $(BUILD_DIR)/paper-final.pdf
REF_START_PAGE ?=
REF_END_PAGE ?=

.PHONY: all prepare assets base pdf qa release render clean distclean

# Default build ALWAYS checks references, links, logs and LaTeX semantics.
all: qa

prepare:
	@mkdir -p $(BUILD_DIR) work
	@case "$(BIB_MODE)" in native|pdf) ;; *) echo 'BIB_MODE must be native or pdf' >&2; exit 2;; esac
	@printf '\\def\\TranslationReferenceMode{%s}\n' '$(BIB_MODE)' > $(BUILD_DIR)/translation-config.tex

assets:
	@python3 scripts/extract_vector_regions.py assets/regions.json --preview-dir work/asset-previews

base: prepare assets
	@latexmk -xelatex -outdir=$(BUILD_DIR) $(MAIN)

pdf: base
	@set -e; if [ "$(BIB_MODE)" = "pdf" ]; then \
	  args=(); \
	  if [ -n "$(REF_START_PAGE)" ]; then args+=(--ref-start-page "$(REF_START_PAGE)"); fi; \
	  if [ -n "$(REF_END_PAGE)" ]; then args+=(--ref-end-page "$(REF_END_PAGE)"); fi; \
	  python3 scripts/add_reference_links.py $(BASE_PDF) $(FINAL_PDF) \
	    --strict --report work/reference-links.json "$${args[@]}"; \
	else \
	  cp $(BASE_PDF) $(FINAL_PDF); \
	fi

qa: pdf
	@python3 scripts/check_latex_project.py $(MAIN) --mode $(BIB_MODE)
	@python3 scripts/check_latex_log.py $(BUILD_DIR)/main.log
	@python3 scripts/audit_pdf.py $(FINAL_PDF) --mode $(BIB_MODE) --strict $(if $(REF_START_PAGE),--ref-start-page $(REF_START_PAGE))
	@echo 'Automated checks passed. Visual inspection + source comparison are STILL required.'

# Release gate: you must populate work/source-blocks.tsv and coverage.tsv.
# A completed ledger does not prove the Chinese translation is accurate.
release: qa
	@python3 scripts/validate_coverage.py work/coverage.tsv \
	    --source-blocks work/source-blocks.tsv --require-nonempty --require-targets --root .
	@python3 scripts/render_pdf.py $(FINAL_PDF) work/final-render --contact-sheet
	@echo 'Review every figure/table/algorithm and the entire page contact sheet before publishing.'

render: pdf
	@python3 scripts/render_pdf.py $(FINAL_PDF) work/final-render --contact-sheet

clean:
	-@latexmk -c -outdir=$(BUILD_DIR) $(MAIN)
	@rm -f $(FINAL_PDF)

distclean:
	-@latexmk -C -outdir=$(BUILD_DIR) $(MAIN)
	@rm -rf $(BUILD_DIR) work/asset-previews work/final-render
