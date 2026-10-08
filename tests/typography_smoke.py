#!/usr/bin/env python3
"""Optional XeLaTeX integration smoke: scientific units + alg refs + small caps."""
from __future__ import annotations

import shutil
import re
import subprocess
import sys
from pathlib import Path

import pymupdf


def main(project: Path) -> None:
    if shutil.which('latexmk') is None:
        raise SystemExit('latexmk required; run this in the CI XeLaTeX job')
    d=project/'work'/'typography-regression'
    d.mkdir(parents=True,exist_ok=True)
    (d/'figures').mkdir(exist_ok=True)
    shutil.copy2(project/'paper-translation.sty',d/'paper-translation.sty')
    with pymupdf.open() as doc:
        page=doc.new_page(width=420,height=68)
        page.insert_text((12,23),'Algorithm 2: Original pseudocode (do not translate)',fontsize=12)
        page.insert_text((12,48),'1: return result',fontsize=10)
        doc.save(d/'figures/alg.pdf')
    (d/'main.tex').write_text(r'''
\documentclass[12pt,a4paper]{scrartcl}
\usepackage{paper-translation}
\begin{document}
单位量纲：\qty{5.4}{\micro\second}；数学环境 $5.4\,\us$。
\zhstrong{中文加粗} and \textsc{Protocol}.
\begin{algorithm}[htbp]
\centering\fbox{Algorithm body only}\caption{独立算法编号}\label{alg:one}
\end{algorithm}
\numberedpreservedalgorithm{figures/alg.pdf}{alg:two}
算法~\ref{alg:one} 与算法~\ref{alg:two} 应分别跳转。
\end{document}
''',encoding='utf-8')
    p=subprocess.run(['latexmk','-xelatex','-interaction=nonstopmode','-halt-on-error',
                      '-outdir=build','main.tex'],cwd=d,capture_output=True,text=True)
    if p.returncode:
        raise SystemExit('XeLaTeX typography smoke FAILED:\n'+(p.stdout+p.stderr)[-4000:])
    audit=subprocess.run([sys.executable,str(project/'scripts/check_latex_log.py'),
                          str(d/'build/main.log')],capture_output=True,text=True)
    if audit.returncode:
        raise SystemExit('LaTeX log audit FAILED:\n'+audit.stdout+audit.stderr)
    pdf=pymupdf.open(d/'build/main.pdf')
    all_text=''.join(page.get_text() for page in pdf)
    if '5.4' not in all_text or 'µs' not in all_text or not re.search(r'算法\s*2', all_text):
        raise SystemExit('Expected units or independent algorithm numbering missing in PDF')
    links=[l for page in pdf for l in page.get_links() if l['kind'] in (pymupdf.LINK_GOTO,pymupdf.LINK_NAMED)]
    if len(links)<2:
        raise SystemExit(f'Expected >=2 working internal algorithm links, found {len(links)}')
    pdf.close()
    print('Typographic XeLaTeX smoke OK: µs, Chinese emphasis, Latin caps, algorithms 1/2 and links')


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python tests/typography_smoke.py <initialized-project-root>')
    main(Path(sys.argv[1]).resolve())
