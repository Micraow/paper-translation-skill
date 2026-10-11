# Contributing

Thanks for considering improvements to **paper-translation**. This is both an agent-facing skill and a small, tested PDF/LaTeX production toolkit.

## Good contributions

- Reproducible bug reports involving reading order, cropped figures, missing links, or TeX compilation.
- Unit tests from **synthetic or redistribution-safe fixtures**; do not commit copyrighted full papers.
- Improvements that preserve original content, scientific data and cross-references.
- Documentation/translation improvements in English and 简体中文.
- Tested compatibility improvements for additional Python/PyMuPDF/TeX Live versions.

## Development

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 scripts/init_project.py /tmp/paper-translation-smoke
cd /tmp/paper-translation-smoke
make
```

The smoke build uses a **labeled placeholder paper**, not a complete translation. CI exercises the same path. End-to-end semantic fidelity must be assessed by comparing to a legally accessible source PDF.

If you touch a PDF manipulation script, include a regression test for the exact failure mode, including annotation behavior when appropriate. If you touch the TeX style, check at least a fresh XeLaTeX build, PDF internal links, the `pdffonts` result, and visual page renders.

## Documentation shape

Keep each rule in **one** place. `SKILL.md` is the only required read and carries the phase
steps; `references/*.md` carry the *why* and the detail, and must not restate a step that
already lives in `SKILL.md`. Compilation traps go in `references/PITFALLS.md`, translation
rules in `references/TRANSLATION.md`, and the delivery checklist in
`references/QA_CHECKLIST.md`. If you are about to write the same paragraph twice, link to
the first copy instead.

### Installing into a local skills directory

When copying the skill to a user skills directory (e.g. `~/.workbuddy/skills/paper-translation/`),
exclude the repository-only weight — it is never read at run time:

```bash
rsync -a --delete \
  --exclude '.git' --exclude 'docs/images' --exclude 'tests' --exclude '__pycache__' \
  ./ ~/.workbuddy/skills/paper-translation/
```

`.git` and `docs/images` are roughly 93% of the on-disk size and serve only the repository.

## PR checklist

- [ ] No personal information, API credentials, proprietary fonts or copyrighted input PDFs added.
- [ ] New/changed script is documented in `SKILL.md` / the appropriate `references/` guide.
- [ ] Unit tests pass and cover the bug fix.
- [ ] `make` passes with XeLaTeX for changes touching the template.
- [ ] Existing features (coverage, vector preservation, bibliography, PDF links) are not weakened.
- [ ] README screenshots truthfully demonstrate rendered output; do not digitally modify technical data.

## Reporting bugs

Please provide: Python/PyMuPDF version; TeX distribution version; relevant error output; minimized synthetic PDF/TeX fixture where possible; expected and actual behavior. **Do not upload proprietary papers publicly without permission.**

By contributing, you agree that your contributions may be distributed under the repository's MIT license, except any explicitly identified third-party components with their own licenses.
