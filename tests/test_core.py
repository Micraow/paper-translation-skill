"""Tests use small, entirely synthetic PDFs; no third-party paper is shipped."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_tool(name: str, *args: str, should_succeed: bool = True):
    result = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str,args)],
                            text=True, capture_output=True)
    if should_succeed and result.returncode != 0:
        raise AssertionError(f"{name} failed: {result.stdout}\n{result.stderr}")
    if not should_succeed and result.returncode == 0:
        raise AssertionError(f"{name} incorrectly passed: {result.stdout}")
    return result


def synthetic_pdf(path: Path, share_empty_annots: bool = False) -> None:
    doc=fitz.open()
    a=doc.new_page()
    a.insert_text((72,92),"Read [1] and [2] for context.", fontsize=12)
    b=doc.new_page()
    b.insert_text((72,92),"Additional results cite [2] and [1].", fontsize=12)
    ref=doc.new_page()
    ref.insert_text((72,92),"References", fontsize=16)
    ref.insert_text((72,130),"[1] A. Author. Example one.", fontsize=11)
    ref.insert_text((72,155),"[2] B. Author. Example two.", fontsize=11)
    if share_empty_annots:
        # Simulate an annotation-removing PDF editor that leaves a single
        # shared empty /Annots array on multiple pages.
        xref = doc.get_new_xref()
        doc.update_object(xref,"[]")
        for i in range(2):
            doc.xref_set_key(doc.page_xref(i),"Annots",f"{xref} 0 R")
    doc.save(path)
    doc.close()


def write_tsv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open('w',encoding='utf8',newline='') as handle:
        w=csv.DictWriter(handle,fieldnames=fieldnames,delimiter='\t')
        w.writeheader()
        w.writerows(rows)


class CoverageTests(unittest.TestCase):
    def test_ledger_fails_for_missing_source_block(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=Path(dirname)
            blocks=d/'source.tsv'; ledger=d/'coverage.tsv'
            write_tsv(blocks,['source_id','page','text'],[
                {'source_id':'p001-b001','page':'1','text':'alpha'},
                {'source_id':'p001-b002','page':'1','text':'beta'}])
            (d/'part.tex').write_text('alpha',encoding='utf-8')
            write_tsv(ledger,['source_id','status','target_file','notes'],[
                {'source_id':'p001-b001','status':'translated','target_file':'part.tex','notes':''}])
            result=run_tool('validate_coverage.py',ledger,'--source-blocks',blocks,
                        '--require-nonempty','--require-targets','--root',d,should_succeed=False)
            self.assertIn('missing source blocks',result.stdout)
            write_tsv(ledger,['source_id','status','target_file','notes'],[
                {'source_id':'p001-b001','status':'translated','target_file':'part.tex','notes':''},
                {'source_id':'p001-b002','status':'skip-with-reason','target_file':'','notes':'duplicate OCR artifact'}])
            run_tool('validate_coverage.py',ledger,'--source-blocks',blocks,
                '--require-nonempty','--require-targets','--root',d)

    def test_blank_ledger_rejected_for_release(self):
        with tempfile.TemporaryDirectory() as dirname:
            p=Path(dirname)/'ledger.tsv'
            write_tsv(p,['source_id','status'],[])
            run_tool('validate_coverage.py',p,'--require-nonempty',should_succeed=False)


class LaTeXTests(unittest.TestCase):
    def test_nested_input_unresolved_cite_fails(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=Path(dirname);(d/'chapters').mkdir()
            (d/'main.tex').write_text(r'\documentclass{article}\begin{document}\input{chapters/a}\end{document}',encoding='utf-8')
            (d/'chapters/a.tex').write_text(r'\input{chapters/b}',encoding='utf-8')
            (d/'chapters/b.tex').write_text(r'Important result~\cite{missing2026}.',encoding='utf-8')
            res=run_tool('check_latex_project.py',d/'main.tex','--mode','native',should_succeed=False)
            self.assertIn('missing2026',res.stdout)
            (d/'chapters/b.tex').write_text(r'Important result~\cite{real2026}.\label{sec:demo}',encoding='utf-8')
            (d/'main.tex').write_text(r'\input{chapters/a}\begin{thebibliography}{9}\bibitem{real2026} A. Author.\end{thebibliography}',encoding='utf-8')
            run_tool('check_latex_project.py',d/'main.tex','--mode','native')

    def test_duplicate_label_and_plain_number_are_rejected(self):
        with tempfile.TemporaryDirectory() as dirname:
            p=Path(dirname)/'main.tex'
            p.write_text(r'\label{eq:x} \label{eq:x} We cite [4].',encoding='utf-8')
            r=run_tool('check_latex_project.py',p,'--mode','native',should_succeed=False)
            self.assertIn('duplicate labels',r.stdout)
            self.assertIn('hard-coded numeric citations',r.stdout)
            p.write_text(r'We cite [4].',encoding='utf-8')
            run_tool('check_latex_project.py',p,'--mode','pdf')


class PdfTests(unittest.TestCase):
    def test_add_reference_links_strict(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=Path(dirname);src=d/'orig.pdf';out=d/'linked.pdf'
            synthetic_pdf(src)
            run_tool('audit_pdf.py',src,'--mode','pdf','--strict',should_succeed=False)
            run_tool('add_reference_links.py',src,out,'--strict')
            doc=fitz.open(out)
            links=[link for pg in doc for link in pg.get_links()]
            self.assertEqual(4,len(links))
            self.assertTrue(all(x['kind']==fitz.LINK_GOTO and x['page']==2 for x in links))
            doc.close()
            run_tool('audit_pdf.py',out,'--mode','pdf','--strict')

    def test_shared_annotation_array_is_not_replicated(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=Path(dirname);src=d/'shared.pdf';out=d/'fixed.pdf';report=d/'report.json'
            synthetic_pdf(src,share_empty_annots=True)
            run_tool('add_reference_links.py',src,out,'--strict','--report',report)
            data=json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(2,data['privatized_annotation_arrays'])
            doc=fitz.open(out)
            self.assertEqual([2,2,0],[len(p.get_links()) for p in doc])
            self.assertEqual(4,sum(len(p.get_links()) for p in doc))
            doc.close()

    def test_pdf_vector_crop_keeps_paths_and_text(self):
        with tempfile.TemporaryDirectory() as dirname:
            d=Path(dirname);src=d/'source.pdf';outdir=d/'figures';manifest=d/'assets.json'
            doc=fitz.open();p=doc.new_page()
            p.draw_rect(fitz.Rect(80,60,180,120),color=(0,0,1),width=2)
            p.insert_text((85,90),'Vector Diagram',fontsize=12)
            doc.save(src);doc.close()
            manifest.write_text(json.dumps({
                'source': str(src),'output_dir': str(outdir),
                'assets':[{'page':1,'bbox':[70,50,200,130],'output':'figure.pdf'}]
            }),encoding='utf-8')
            run_tool('extract_vector_regions.py',manifest)
            extracted=fitz.open(outdir/'figure.pdf')
            self.assertEqual(1,len(extracted))
            self.assertGreater(len(extracted[0].get_drawings()),0)
            self.assertIn('Vector Diagram',extracted[0].get_text())
            extracted.close()


if __name__=='__main__':
    unittest.main()
