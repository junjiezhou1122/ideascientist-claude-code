import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from native_fixture import create_run

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_checker', ROOT / 'scripts/check_artifacts.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = create_run(Path(self.temp.name) / 'offline-test')

    def change(self, name, mutate):
        path = self.root / name
        value = json.loads(path.read_text())
        mutate(value)
        path.write_text(json.dumps(value))

    def rejects(self, phrase):
        failures = checker.check_run(self.root)
        self.assertTrue(any(phrase in error for error in failures), failures)

    def test_synthetic_complete_run_passes(self):
        self.assertEqual(checker.check_run(self.root), [])

    def test_invented_reference_fails(self):
        self.change('report.json', lambda d: d.update(title='Invented [P999]'))
        self.rejects('P999 has no registered read digest')

    def test_unread_registered_paper_fails(self):
        (self.root / 'papers/P001.json').unlink()
        self.rejects('P001 has no registered read digest')

    def test_missing_locator_fails(self):
        self.change('report-evidence.json', lambda d: d['supports'][0].update(locator='Missing Section'))
        self.rejects('does not match an answered goal and locator')

    def test_abstract_cannot_support_mechanism(self):
        self.change('papers/P001.json', lambda d: (d.update(access_level='abstract'), d['answers'][0].update(access_level='abstract', locator='Abstract')))
        for name in ('gaps/A001.json', 'candidates/C001.json', 'reviews/C001.json', 'baselines/G001.json', 'report-evidence.json'):
            self.change(name, lambda d: d['supports'][0].update(locator='Abstract'))
        self.rejects('abstract-only support cannot back mechanism')

    def test_exact_version_unknown_cutoff_fails(self):
        self.change('run.json', lambda d: d['papers'][0]['identity'].update(publication_date=None))
        self.change('papers/P001.json', lambda d: d['identity'].update(publication_date=None))
        self.rejects('exact source version date unknown or after cutoff')

    def test_exact_version_after_cutoff_fails(self):
        self.change('run.json', lambda d: d['papers'][0]['identity'].update(publication_date='2021-01-01', version='synthetic v2'))
        self.change('papers/P001.json', lambda d: d['identity'].update(publication_date='2021-01-01', version='synthetic v2'))
        self.rejects('exact source version date unknown or after cutoff')

    def test_current_candidate_requires_its_own_review(self):
        candidate = json.loads((self.root / 'candidates/C001.json').read_text())
        candidate['candidate_id'] = 'C002'
        (self.root / 'candidates/C002.json').write_text(json.dumps(candidate))
        self.change('run.json', lambda d: (d['selected'].update(candidate_id='C002'), d['next_ids'].update(candidate=3)))
        self.rejects('selected current candidate must be reviewed')

    def test_revision_after_reject_fails(self):
        candidate = json.loads((self.root / 'candidates/C001.json').read_text())
        candidate.update(candidate_id='C002', prior_candidate='C001', revision=1)
        (self.root / 'candidates/C002.json').write_text(json.dumps(candidate))
        self.change('run.json', lambda d: d['next_ids'].update(candidate=3))
        self.change('reviews/C001.json', lambda d: d.update(verdict='reject'))
        self.rejects('revision requires a revise verdict')

    def test_nested_evaluation_fields_required(self):
        self.change('report.json', lambda d: d['proposed_evaluation'].pop('ablations'))
        self.rejects('proposed_evaluation.ablations: required')

    def test_prediction_requires_kill_condition(self):
        self.change('report.json', lambda d: d['falsifiable_predictions'][0].pop('kill_condition'))
        self.rejects('kill_condition: required')

    def test_blind_baseline_must_have_safe_inputs(self):
        self.change('baselines/G001.json', lambda d: d['input_files'].append('candidates/C001.json'))
        self.rejects('baseline inputs must be proposal-blind')

    def test_missing_baseline_cannot_claim_enabled_comparison(self):
        (self.root / 'baselines/G001.json').unlink()
        self.rejects('enabled blind baseline must freeze before candidate')

    def test_zero_gap_is_valid(self):
        for directory in ('candidates', 'reviews', 'baselines'):
            for path in (self.root / directory).glob('*.json'):
                path.unlink()
        (self.root / 'report.json').unlink()
        (self.root / 'report-evidence.json').unlink()
        self.change('gaps/A001.json', lambda d: d.update(gaps=[], outcome='no_gap'))
        self.change('run.json', lambda d: (d.update(stage='gaps', status='no_gap'), d['selected'].update(gap_id=None, candidate_id=None)))
        self.assertEqual(checker.check_run(self.root), [])

    def test_malformed_date_is_reported(self):
        self.change('run.json', lambda d: d.update(cutoff='2020-99-01'))
        self.rejects('run.json.cutoff: no allowed type matches')

    def test_budget_exhaustion_is_visible(self):
        self.change('run.json', lambda d: d['budgets']['searches'].update(spent=41))
        self.rejects('spent exceeds limit')

    def test_same_candidate_id_with_changed_content_invalidates_review(self):
        self.change('candidates/C001.json', lambda d: d.update(Intuition='A different mechanism.'))
        self.rejects('candidate changed since review')
        self.rejects('candidate changed since report')

    def test_changed_gap_invalidates_candidate_and_baseline(self):
        self.change('gaps/A001.json', lambda d: d['gaps'][0].update(Gap='A different deficiency [P001].'))
        self.rejects('gap changed since candidate creation')
        self.rejects('gap changed since baseline freeze')

    def test_changed_answer_with_same_locator_invalidates_support(self):
        self.change('papers/P001.json', lambda d: d['answers'][0].update(answer='The mechanism needs a different assumption.'))
        self.rejects('answer changed since receipt')

    def test_report_edit_invalidates_evidence_receipt(self):
        self.change('report.json', lambda d: d.update(title='An edited proposal'))
        self.rejects('report changed since evidence receipt')

    def test_failed_followup_preserves_existing_support(self):
        self.change('papers/P001.json', lambda d: d['answers'].append({'goal': 'An inaccessible follow-up question', 'answer': 'Follow-up access failed.', 'locator': None, 'status': 'unavailable', 'access_level': 'unavailable'}))
        self.assertEqual(checker.check_run(self.root), [])

    def test_unknown_date_is_allowed_in_live_mode(self):
        self.change('run.json', lambda d: (d.update(cutoff=None), d['papers'][0]['identity'].update(publication_date=None, date_basis='unknown')))
        self.change('papers/P001.json', lambda d: d['identity'].update(publication_date=None, date_basis='unknown'))
        self.assertEqual(checker.check_run(self.root), [])

    def test_missing_baseline_recovery_disables_comparison(self):
        (self.root / 'baselines/G001.json').unlink()
        self.change('run.json', lambda d: d.update(blind_baseline=False, reason='Baseline irrecoverably unavailable; no nonobviousness comparison.'))
        self.assertEqual(checker.check_run(self.root), [])

    def test_empty_blocked_discovery_preserves_honest_failure(self):
        discovery = {'task_id': 'T001', 'role': 'gap-finder', 'sources': [],
                     'search': {'queries': ['synthetic metadata query'], 'coverage': 'Links lacked exact metadata.',
                                'status': 'blocked', 'block_reason': 'Exact metadata could not be resolved.'}}
        task = {'task_id': 'T001', 'role': 'gap-finder', 'target': 'A001', 'output': 'discoveries/T001.json',
                'status': 'blocked', 'search_allowance': 2, 'reader_allowance': 0}
        self.change('run.json', lambda d: (d['tasks'].append(task), d['next_ids'].update(task=2)))
        directory = self.root / 'discoveries'
        directory.mkdir()
        (directory / 'T001.json').write_text(json.dumps(discovery))
        self.assertEqual(checker.check_run(self.root), [])

    def test_markdown_unknown_citation_fails(self):
        (self.root / 'plan.md').write_text('Unregistered [P888]')
        self.rejects('P888 has no registered read digest')


if __name__ == '__main__':
    unittest.main()
