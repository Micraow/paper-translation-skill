SHELL := /bin/bash
.DEFAULT_GOAL := all

MAIN ?= main.tex
BUILD_DIR ?= build
BIB_MODE ?= native
BASE_PDF := $(BUILD_DIR)/main.pdf
FINAL_PDF := $(BUILD_DIR)/paper-final.pdf
REF_START_PAGE ?=
REF_END_PAGE ?=

# The reference backend is a source-level choice, so its generated configuration
# lives at a fixed path independent of BUILD_DIR. main.tex \input's exactly this
# path; changing it here without changing main.tex silently selects the wrong
# bibliography backend.
CONFIG_TEX := work/translation-config.tex

# Vector crops are re-derived only when the manifest or the source PDF changes,
# so a plain `make` never rewrites an already reviewed figures/ directory.
REGION_MANIFEST := assets/regions.json
REGION_SOURCES := $(REGION_MANIFEST) $(wildcard sources/original.pdf)
ASSET_STAMP := work/asset-previews/.extracted

.PHONY: all prepare assets base pdf qa release render source-blocks seed-coverage packets clean distclean

# Default build ALWAYS checks references, links, logs and LaTeX semantics.
all: qa

prepare:
	@mkdir -p $(BUILD_DIR) work
	@case "$(BIB_MODE)" in native|pdf) ;; *) echo 'BIB_MODE must be native or pdf' >&2; exit 2;; esac
	@printf '\\def\\TranslationReferenceMode{%s}\n' '$(BIB_MODE)' > $(CONFIG_TEX)

assets: $(ASSET_STAMP)

$(ASSET_STAMP): $(REGION_SOURCES)
	@python3 scripts/extract_vector_regions.py $(REGION_MANIFEST) --preview-dir work/asset-previews
	@mkdir -p $(dir $(ASSET_STAMP)) && touch $@

base: prepare assets
	@python3 scripts/check_latex_project.py $(MAIN) --mode $(BIB_MODE)
	@python3 scripts/run_latexmk.py --main $(MAIN) --build-dir $(BUILD_DIR)

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
	@python3 scripts/check_latex_log.py $(BUILD_DIR)/main.log
	@python3 scripts/audit_pdf.py $(FINAL_PDF) --mode $(BIB_MODE) --strict $(if $(REF_START_PAGE),--ref-start-page $(REF_START_PAGE))
	@echo 'Automated checks passed. Visual inspection + source comparison are STILL required.'

# Draft coverage mapping: never marks blocks as reviewed. Prepare
# assets/coverage-map.json by reading the actual source page headings first.
source-blocks:
	@test -f sources/original.pdf || { echo 'Missing sources/original.pdf' >&2; exit 2; }
	@python3 scripts/extract_text_blocks.py sources/original.pdf --tsv work/source-blocks.tsv

seed-coverage: source-blocks
	@test -f assets/coverage-map.json || { echo 'First copy/edit assets/coverage-map.example.json to assets/coverage-map.json' >&2; exit 2; }
	@python3 scripts/seed_coverage.py work/source-blocks.tsv \
	    --headings assets/coverage-map.json --regions assets/regions.json \
	    --project-root . --output work/coverage.tsv

# Compact per-section context routing (does not certify coverage or make a model call).
packets:
	@python3 scripts/prepare_section_packets.py --source-blocks work/source-blocks.tsv \
	    --ledger work/coverage.tsv --headings assets/coverage-map.json

# Release gate: you must populate work/source-blocks.tsv and coverage.tsv.
# A completed ledger does not prove the Chinese translation is accurate.
# The final block prints exactly which checks ran and which did not, so a green
# build cannot be described as "fully verified".
release: qa
	@python3 scripts/validate_coverage.py work/coverage.tsv \
	    --source-blocks work/source-blocks.tsv --require-nonempty --require-targets --root .
	@python3 scripts/render_pdf.py $(FINAL_PDF) work/final-render --contact-sheet
	@echo ''
	@echo 'Release gate — checks that RAN automatically:'
	@echo '  [x] XeLaTeX build + recursive project/reference/citation lint'
	@echo '  [x] TeX log audit (missing glyph, undefined ref/cite, font-shape substitution)'
	@echo '  [x] PDF link audit (GoTo + named destinations, strict)'
	@echo '  [x] Coverage ledger vs extracted source blocks (structural traceability)'
	@echo '  [x] Full-page render + contact sheet'
	@echo 'Checks that did NOT run — still required from a human or a visual model:'
	@echo '  [ ] Semantic source-to-translation comparison (column joins, equations, qualifiers)'
	@echo '  [ ] Visual framing of every figure/table/algorithm crop'
	@echo '  [ ] Click-through spot check of citation/equation links in the final PDF'
	@echo 'Do not report this build as "fully reviewed" on the strength of the [x] lines.'

render: pdf
	@python3 scripts/render_pdf.py $(FINAL_PDF) work/final-render --contact-sheet

clean:
	-@latexmk -c -outdir=$(BUILD_DIR) $(MAIN)
	@rm -f $(FINAL_PDF)

distclean:
	-@latexmk -C -outdir=$(BUILD_DIR) $(MAIN)
	@rm -rf $(BUILD_DIR) work/asset-previews work/final-render $(CONFIG_TEX)
