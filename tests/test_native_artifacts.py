import importlib.util
import json
import subprocess
import sys
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

    def test_baseline_metadata_requires_run_relative_scientific_paths(self):
        inputs = ['problem.md', 'gaps/A001.json', 'papers/P001.json']
        invalid_inputs = [[str(self.root / path) for path in inputs],
                          ['problem.md', 'gaps/A001.json', './papers/P001.json']]
        for control in ('references/roles/blind-baseline.md', 'adapters/claude/binding.md',
                        'references/contracts.md', 'references/artifacts.schema.json'):
            invalid_inputs.append(inputs + [str(ROOT / control)])
        for path in ('run.json', 'plan.md', 'reviews/C001.json', 'report.json'):
            invalid_inputs.append(inputs + [path])
        for paths in invalid_inputs:
            with self.subTest(paths=paths):
                self.change('baselines/G001.json', lambda d: d.update(input_files=paths))
                self.rejects('baseline inputs must be proposal-blind allowlist')
                self.rejects('blind baseline input metadata must resolve exactly')
        self.change('baselines/G001.json', lambda d: d.update(input_files=inputs))
        self.assertEqual(checker.check_run(self.root), [])

    def test_baseline_metadata_requires_exact_scientific_inputs(self):
        inputs = ['problem.md', 'gaps/A001.json', 'papers/P001.json']
        for missing in inputs:
            with self.subTest(missing=missing):
                self.change('baselines/G001.json', lambda d: d.update(input_files=[path for path in inputs if path != missing]))
                self.rejects('blind baseline input metadata must resolve exactly')
        self.change('baselines/G001.json', lambda d: d.update(input_files=inputs + ['papers/P002.json']))
        self.rejects('blind baseline input metadata must resolve exactly')
        self.change('baselines/G001.json', lambda d: d.update(input_files=inputs, input_paper_ids=['P001', 'P002']))
        self.rejects('blind baseline input metadata must resolve exactly')
        self.rejects('baseline may see only problem and near-miss digests')

    def test_baseline_requires_frozen_unexposed_and_earlier_marker(self):
        for updates, error in (({'frozen': False}, 'frozen: expected constant True'),
                               ({'proposal_exposed': True}, 'proposal_exposed: expected constant False'),
                               ({'before_candidate': 'C002'}, 'baseline freeze marker is after candidate exposure')):
            with self.subTest(updates=updates):
                self.change('baselines/G001.json', lambda d: d.update(frozen=True, proposal_exposed=False, before_candidate='C001'))
                self.change('baselines/G001.json', lambda d: d.update(updates))
                self.rejects(error)

    def test_missing_baseline_cannot_claim_enabled_comparison(self):
        (self.root / 'baselines/G001.json').unlink()
        self.rejects('enabled blind baseline must freeze before candidate')

    def zero_gap_run(self):
        for directory in ('candidates', 'reviews', 'baselines'):
            for path in (self.root / directory).glob('*.json'):
                path.unlink()
        (self.root / 'report.json').unlink()
        (self.root / 'report-evidence.json').unlink()
        self.change('gaps/A001.json', lambda d: d.update(gaps=[], outcome='no_gap'))
        self.change('run.json', lambda d: (d.update(stage='gaps', status='no_gap'), d['selected'].update(gap_id=None, candidate_id=None)))

    def test_zero_gap_is_valid(self):
        self.zero_gap_run()
        self.assertEqual(checker.check_run(self.root), [])

    def test_zero_gap_array_indexing_passes_cli(self):
        self.zero_gap_run()
        self.change('gaps/A001.json', lambda d: d['search'].update(coverage='SYNTHETIC coverage uses sources[0] and sources[3].'))
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/check_artifacts.py'), str(self.root), '--json'], capture_output=True, text=True)
        output = json.loads(result.stdout)
        self.assertEqual(output, {'ok': True, 'errors': []})
        self.assertEqual(result.returncode, 0)

    def test_identifier_numeric_indexing_is_not_a_citation(self):
        for text in ('sources[0]', '_sources_2[3]', 'obj.sources[1]'):
            with self.subTest(text=text):
                self.assertEqual(checker.cited_ids(text), (set(), []))

    def test_nested_invalid_citations_are_reported_once(self):
        self.zero_gap_run()
        for text, bracket in (('Standalone [1].', '1'), ('Grouped [P001,P002].', 'P001,P002'),
                              ('sources[P001,P002]', 'P001,P002')):
            with self.subTest(text=text):
                self.change('gaps/A001.json', lambda d: d['search'].update(coverage=text))
                self.assertEqual(checker.check_run(self.root), [f'gaps/A001.json: invalid citation [{bracket}]; use one stable P ID per bracket'])

    def test_numeric_bibliographic_brackets_still_fail(self):
        for text in ('[1]', '([1])', '2024[1]'):
            with self.subTest(text=text):
                self.assertEqual(checker.cited_ids(text), (set(), ['invalid citation [1]; use one stable P ID per bracket']))

    def test_identifier_attached_p_references_still_require_read_digest(self):
        for text in ('sources[P999]', 'Unknown [P999]'):
            with self.subTest(text=text):
                (self.root / 'plan.md').write_text(text)
                self.rejects('P999 has no registered read digest')
        (self.root / 'plan.md').write_text('Known sources[P001] and [P001].')
        self.assertEqual(checker.check_run(self.root), [])

    def test_nested_structured_citation_fields_preserve_ids(self):
        for field in ('paper_id', 'citations', 'near_miss_ids', 'source_ids', 'closest_in_domain_ids', 'input_paper_ids'):
            with self.subTest(field=field):
                value = 'P999' if field == 'paper_id' else ['P999']
                self.assertEqual(checker.cited_ids({'nested': [{field: value}]}), ({'P999'}, []))

    def test_markdown_invalid_citation_is_reported_once_with_valid_p_id(self):
        for text in ('Standalone [1].', 'Standalone [1] with known [P001].'):
            with self.subTest(text=text):
                (self.root / 'plan.md').write_text(text)
                self.assertEqual(checker.check_run(self.root), ['plan.md: invalid citation [1]; use one stable P ID per bracket'])

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

    def discovery(self, sources=None):
        identity = json.loads((self.root / 'papers/P001.json').read_text())['identity']
        value = {'task_id': 'T001', 'role': 'gap-finder', 'sources': [] if sources is None else sources,
                 'search': {'queries': ['synthetic metadata query'], 'coverage': 'Search returned links without exact metadata.',
                            'status': 'blocked', 'block_reason': 'Exact author and version metadata could not be resolved.'}}
        task = {'task_id': 'T001', 'role': 'gap-finder', 'target': 'A001', 'output': 'discoveries/T001.json',
                'status': 'blocked', 'search_allowance': 2, 'reader_allowance': 0}
        self.change('run.json', lambda d: (d['tasks'].append(task), d['next_ids'].update(task=2)))
        directory = self.root / 'discoveries'
        directory.mkdir(exist_ok=True)
        (directory / 'T001.json').write_text(json.dumps(value))
        return identity

    def test_empty_blocked_discovery_preserves_honest_failure(self):
        self.discovery()
        self.assertEqual(checker.check_run(self.root), [])

    def test_empty_discovery_requires_blocked_search_and_substantive_reason(self):
        self.discovery()
        for updates in ({'status': 'searched'}, {'block_reason': None}, {'block_reason': '  '}):
            with self.subTest(updates=updates):
                self.change('discoveries/T001.json', lambda d: d['search'].update(status='blocked', block_reason='Metadata unavailable.'))
                self.change('discoveries/T001.json', lambda d: d['search'].update(updates))
                self.rejects('no allowed type matches')

    def test_empty_discovery_requires_matching_blocked_task(self):
        self.discovery()
        for updates in ({'status': 'needs_registration'}, {'role': 'reviewer'}, {'output': 'gaps/A001.json'}):
            with self.subTest(updates=updates):
                self.change('run.json', lambda d: d['tasks'][0].update(status='blocked', role='gap-finder', output='discoveries/T001.json'))
                self.change('run.json', lambda d: d['tasks'][0].update(updates))
                self.rejects('empty blocked discovery requires matching blocked task, role, and output')
        self.change('run.json', lambda d: d.update(tasks=[]))
        self.rejects('empty blocked discovery requires matching blocked task, role, and output')

    def test_empty_discovery_rejects_unknown_fields_and_invalid_role(self):
        self.discovery()
        self.change('discoveries/T001.json', lambda d: d.update(extra='Cannot bypass strict schema.'))
        self.rejects('no allowed type matches')
        self.change('discoveries/T001.json', lambda d: (d.pop('extra'), d.update(role='paper-reader')))
        self.rejects('no allowed type matches')

    def test_legacy_nonempty_discovery_still_passes_and_checks_cutoff(self):
        identity = self.discovery()
        self.change('discoveries/T001.json', lambda d: d.update(sources=[{'identity': identity, 'goals': ['What is the mechanism?']}]))
        self.change('discoveries/T001.json', lambda d: d['search'].update(status='searched', block_reason=None))
        self.change('run.json', lambda d: d['tasks'][0].update(status='needs_registration'))
        self.assertEqual(checker.check_run(self.root), [])
        self.change('discoveries/T001.json', lambda d: d['sources'][0]['identity'].update(publication_date='2021-01-01'))
        self.rejects('exact source version date unknown or after cutoff')

    def reader_relay_run(self):
        for directory in ('gaps', 'candidates', 'reviews', 'baselines'):
            for path in (self.root / directory).glob('*.json'):
                path.unlink()
        (self.root / 'report.json').unlink()
        (self.root / 'report-evidence.json').unlink()
        tasks = [
            {'task_id': 'T001', 'role': 'gap-finder', 'target': 'A001 registered reading handoff',
             'output': 'gaps/A001.json', 'status': 'reader_relay', 'search_allowance': 0, 'reader_allowance': 1},
            {'task_id': 'T002', 'role': 'paper-reader', 'target': 'P001 under T001 reservation',
             'output': 'papers/P001.json', 'status': 'active', 'search_allowance': 0, 'reader_allowance': 0},
        ]
        self.change('run.json', lambda d: (d.update(stage='planned', status='active', tasks=tasks),
                                           d['selected'].update(axis_id=None, gap_id=None, candidate_id=None),
                                           d['next_ids'].update(task=3),
                                           d['budgets']['role_calls'].update(spent=2),
                                           d['budgets']['reader_calls'].update(spent=1)))

    def test_completed_reader_relay_allows_one_active_reader_without_gap_output(self):
        self.reader_relay_run()
        self.assertEqual(checker.check_run(self.root), [])

    def test_reader_relay_does_not_relax_sequential_dispatch(self):
        self.reader_relay_run()
        task = {'task_id': 'T003', 'role': 'gap-finder', 'target': 'A001 continuation',
                'output': 'gaps/A001.json', 'status': 'active', 'search_allowance': 0, 'reader_allowance': 0}
        self.change('run.json', lambda d: (d['tasks'].append(task), d['next_ids'].update(task=4)))
        self.rejects('sequential dispatch requires at most one active task')

    def test_reader_relay_cannot_advance_to_missing_gap(self):
        self.reader_relay_run()
        self.change('run.json', lambda d: (d.update(stage='gaps'), d['selected'].update(axis_id='A001', gap_id='G001')))
        self.rejects('stage gaps: selected axis output required')

    def test_done_task_still_requires_output_after_relay_support(self):
        self.reader_relay_run()
        self.change('run.json', lambda d: d['tasks'][0].update(status='done'))
        self.rejects('done task has missing output')

    def test_markdown_unknown_citation_fails(self):
        (self.root / 'plan.md').write_text('Unregistered [P888]')
        self.rejects('P888 has no registered read digest')


if __name__ == '__main__':
    unittest.main()
