"""Regressions distilled from actual agent use on a two-column systems paper."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def call(script: str, *args, success: bool = True):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                       capture_output=True, text=True)
    if (p.returncode == 0) != success:
        raise AssertionError(f"unexpected exit {p.returncode}: {p.stdout}\n{p.stderr}")
    return p


def tsv(path: Path, fields: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, delimiter='\t', fieldnames=fields)
        w.writeheader(); w.writerows(rows)


class MacroLintRegressions(unittest.TestCase):
    def test_argument_count_is_not_numeric_citation_but_real_citation_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'main.tex'
            p.write_text(r'\newcommand{\func}[1]{{\capsfont #1}}'
                         '\n' + r'\newenvironment{foo}[2]{}{}', encoding='utf-8')
            call('check_latex_project.py', p, '--mode', 'native')
            p.write_text(r'\newcommand{\func}[1]{#1} See also [7, 11].', encoding='utf-8')
            result=call('check_latex_project.py',p,'--mode','native',success=False)
            self.assertIn('hard-coded numeric citations',result.stdout)

    def test_known_unicode_math_unit_trap_blocked_early(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'main.tex'
            p.write_text(r'Speed 5.4 $\mathrm{\mu s}$.',encoding='utf-8')
            result=call('check_latex_project.py',p,'--mode','native',success=False)
            self.assertIn('micro',result.stdout.lower())
            p.write_text(r'\qty{5.4}{\micro\second}',encoding='utf-8')
            call('check_latex_project.py',p,'--mode','native')

    def test_chinese_emphasis_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'main.tex'
            p.write_text(r'\emph{中文重点} and \emph{English}', encoding='utf-8')
            result=call('check_latex_project.py',p,'--mode','native',success=False)
            self.assertIn('CJK may lose emphasis',result.stdout)
            relaxed=call('check_latex_project.py',p,'--mode','native','--allow-cjk-emph')
            self.assertIn('WARN:',relaxed.stdout)
            p.write_text(r'\zhstrong{中文重点} and \emph{English}', encoding='utf-8')
            result=call('check_latex_project.py',p,'--mode','native')
            self.assertNotIn('CJK may lose emphasis',result.stdout)

    def test_missing_italic_or_smallcaps_shape_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            log=Path(tmp)/'main.log'
            log.write_text("LaTeX Font Warning: Font shape `TU/SourceHanSerifCN(0)/m/it' undefined\n"
                           "(Font) using `TU/SourceHanSerifCN(0)/m/n' instead.\n",encoding='utf-8')
            r=call('check_latex_log.py',log,success=False)
            self.assertIn('font_shape_substitution: 1',r.stdout)
            r=call('check_latex_log.py',log,'--allow-font-substitutions')
            self.assertIn('LaTeX log OK',r.stdout)


class LedgerRegressions(unittest.TestCase):
    @staticmethod
    def sample(d: Path):
        blocks=d/'work'/'source-blocks.tsv'
        columns=['source_id','page','block','x0','y0','x1','y1','text']
        # Intentionally scrambled block ids; two-column ordering is semantic.
        rows=[
            dict(source_id='p001-b003',page=1,block=3,x0=343,y0=50,x1=480,y1=92,text='Original algorithm body'),
            dict(source_id='p001-b001',page=1,block=1,x0=45,y0=20,x1=180,y1=38,text='Abstract'),
            dict(source_id='p001-b002',page=1,block=2,x0=45,y0=80,x1=250,y1=110,text='Precisely measured delay'),
            dict(source_id='p001-b004',page=1,block=4,x0=45,y0=310,x1=285,y1=336,text='1 Introduction'),
            dict(source_id='p001-b005',page=1,block=5,x0=45,y0=775,x1=240,y1=790,text='USENIX Association'),
            dict(source_id='p002-b001',page=2,block=1,x0=45,y0=30,x1=220,y1=42,text='References'),
            dict(source_id='p002-b002',page=2,block=2,x0=45,y0=60,x1=275,y1=80,text='[1] First article'),
        ]
        tsv(blocks,columns,rows)
        (d/'sections').mkdir(exist_ok=True)
        for f in ('00-abstract.tex','01-introduction.tex','references.tex'):
            (d/'sections'/f).write_text('Reviewed text placeholder',encoding='utf-8')
        (d/'figures').mkdir(exist_ok=True)
        (d/'figures/algorithm01.pdf').write_bytes(b'%PDF-1.0 dummy asset file')
        (d/'assets').mkdir(exist_ok=True)
        cfg={
            'reading_order':'two-column', 'column_split_x':300,
            'headings':[
                {'match':'^Abstract\\b','target_file':'sections/00-abstract.tex'},
                {'match':'^1\\s+Introduction\\b','target_file':'sections/01-introduction.tex'},
                {'match':'^References\\b','target_file':'sections/references.tex','status':'preserved'},
            ],
            'furniture_patterns':['^USENIX Association']
        }
        (d/'assets/map.json').write_text(json.dumps(cfg),encoding='utf-8')
        manifest={'source':'../sources/original.pdf','output_dir':'../figures',
                  'assets':[{'page':1,'bbox':[330,40,490,120],
                             'output':'algorithm01.pdf','kind':'algorithm'}]}
        (d/'assets/regions.json').write_text(json.dumps(manifest),encoding='utf-8')
        return blocks,d/'assets/map.json',d/'assets/regions.json'

    def test_heading_assertion_and_vector_crop_proposals_still_all_todo(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            blocks,headings,regions=self.sample(d)
            ledger=d/'work/coverage.tsv'
            call('seed_coverage.py',blocks,'--headings',headings,'--regions',regions,
                 '--project-root',d,'--output',ledger)
            with ledger.open(encoding='utf-8') as f:
                rows={r['source_id']:r for r in csv.DictReader(f,delimiter='\t')}
            self.assertEqual(7,len(rows))
            self.assertEqual({'todo'},{r['status'] for r in rows.values()})
            self.assertEqual('sections/01-introduction.tex',rows['p001-b004']['suggested_target'])
            self.assertEqual('preserved',rows['p001-b003']['suggested_status'])
            self.assertEqual('figures/algorithm01.pdf',rows['p001-b003']['suggested_target'])
            self.assertEqual('nonprose',rows['p001-b005']['suggested_status'])
            self.assertEqual('',rows['p001-b005']['suggested_target'])
            call('validate_coverage.py',ledger,'--source-blocks',blocks,
                 '--require-nonempty','--require-targets','--root',d,success=False)
            # Bad heading regex must FAIL rather than silently map later sections.
            cfg=json.loads(headings.read_text())
            cfg['headings'][1]['match']='^2 Results'
            headings.write_text(json.dumps(cfg),encoding='utf-8')
            out=d/'work/should-not-exist.tsv'
            result=call('seed_coverage.py',blocks,'--headings',headings,'--regions',regions,
                        '--project-root',d,'--output',out,success=False)
            self.assertIn('matched 0 time',result.stdout)
            self.assertFalse(out.exists())

    def test_seed_refuses_to_destroy_populated_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); blocks, headings, regions=self.sample(d)
            ledger=d/'work/coverage.tsv'
            call('seed_coverage.py',blocks,'--headings',headings,'--regions',regions,
                 '--project-root',d,'--output',ledger)
            original=ledger.read_bytes()
            result=call('seed_coverage.py',blocks,'--headings',headings,'--regions',regions,
                        '--project-root',d,'--output',ledger,success=False)
            self.assertIn('refusing to overwrite',result.stderr)
            self.assertEqual(original,ledger.read_bytes())
            call('seed_coverage.py',blocks,'--headings',headings,'--regions',regions,
                 '--project-root',d,'--output',ledger,'--force')

    def test_confirmation_records_review_and_preserved_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            blocks,headings,regions=self.sample(d)
            ledger=d/'work/coverage.tsv'
            call('seed_coverage.py',blocks,'--headings',headings,'--regions',regions,
                 '--project-root',d,'--output',ledger)
            call('confirm_coverage.py',ledger,'--status','preserved',
                 '--target','figures/algorithm01.pdf','--project-root',d,
                 '--review-note','Compared complete original algorithm page and crop')
            with ledger.open(encoding='utf-8') as f:
                rows={r['source_id']:r for r in csv.DictReader(f,delimiter='\t')}
            self.assertEqual('preserved',rows['p001-b003']['status'])
            self.assertEqual('todo',rows['p001-b002']['status'])
            self.assertIn('Compared complete',rows['p001-b003']['notes'])

    def test_nonprose_cannot_pretend_to_point_to_equation_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); ledger=d/'coverage.tsv'
            tsv(ledger,['source_id','status','target_file','notes'],[
                dict(source_id='p001-b001',status='nonprose',target_file='figures/eq.pdf',notes='')])
            res=call('validate_coverage.py',ledger,'--require-targets',success=False)
            self.assertIn('nonprose must have an empty',res.stdout)


class ExtractRegressions(unittest.TestCase):
    def test_c0_control_does_not_poison_tsv_and_is_visibly_marked(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('sourceblocks',SCRIPTS/'extract_text_blocks.py')
        mod=importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        cleaned=mod.clean_text('Flow\x02rate\x1b = \x07mu')
        self.assertEqual('Flow\ufffdrate\ufffd = \ufffdmu',cleaned)
        self.assertFalse(any(ord(c)<32 for c in cleaned))
        self.assertEqual('A\x02B\x1cC',mod.clean_text('A\x02B\x1cC',keep_raw=True))


if __name__ == '__main__':
    unittest.main()
