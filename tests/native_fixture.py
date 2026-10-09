"""Explicitly synthetic offline artifacts. No real paper evidence or research results."""

import json
from pathlib import Path


def create_run(path):
    root = Path(path)
    root.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, indent=2) + '\n')

    identity = {'title': 'SYNTHETIC offline mechanism note', 'authors': ['Offline fixture'], 'url': 'https://example.invalid/offline-note-v1', 'doi': None, 'version': 'synthetic v1', 'publication_date': '2020-01-01', 'date_basis': 'Synthetic fixture date, not a publication claim'}
    goal = 'What assumption does the synthetic mechanism require?'
    support = {'paper_id': 'P001', 'goal': goal, 'locator': 'Section synthetic mechanism', 'claim': 'Synthetic mechanism requires a stable signal.', 'kind': 'mechanism'}
    search = {'queries': ['synthetic offline query'], 'coverage': 'SYNTHETIC offline search trace, no web retrieval.', 'status': 'searched', 'block_reason': None}
    run = {'schema_version': 1, 'slug': root.name, 'problem': 'SYNTHETIC offline test problem', 'challenge': 'SYNTHETIC signal instability', 'language': 'English', 'cutoff': '2020-12-31', 'stage': 'report', 'status': 'complete', 'reason': 'SYNTHETIC fixture for structural validation only', 'axes': [{'axis_id': 'A001', 'name': 'Synthetic signal stability'}], 'selected': {'axis_id': 'A001', 'gap_id': 'G001', 'candidate_id': 'C001'}, 'next_ids': {'paper': 2, 'gap': 2, 'candidate': 2, 'task': 1}, 'budgets': {name: {'limit': limit, 'spent': 0} for name, limit in [('role_calls', 24), ('searches', 40), ('reader_calls', 18)]}, 'max_revisions': 2, 'max_candidates_per_gap': 3, 'blind_baseline': True, 'papers': [{'paper_id': 'P001', 'identity': identity}], 'tasks': []}
    save('run.json', run)
    (root / 'plan.md').write_text('# SYNTHETIC offline plan\nNo actual agents or literature retrieval.\n')
    (root / 'problem.md').write_text('# SYNTHETIC offline problem\nA signal may be unstable.\n')
    save('papers/P001.json', {'paper_id': 'P001', 'identity': identity, 'access_level': 'full_text', 'read_status': 'read', 'results_masked': True, 'views': {'problem_definition': 'Synthetic stable-signal task.', 'challenge': 'Synthetic instability.', 'intuition': 'Synthetic stabilizer.', 'solution': 'Synthetic signal filter, no claimed outcome.'}, 'answers': [{'goal': goal, 'answer': 'This synthetic note requires a stable signal.', 'locator': support['locator'], 'status': 'answered', 'access_level': 'full_text'}], 'limitations': ['Synthetic evidence only.']})
    gap = {'gap_id': 'G001', 'Gap': 'Synthetic methods require a stable signal [P001].', 'Near-miss methods and coverage': 'Synthetic filter is a narrow near miss [P001].', 'Methodological deficiency': 'Synthetic assumption fails under a changing signal [P001].', 'Why it matters': 'Synthetic downstream users need changing signals.', 'Evidence route': 'Observe consistency under synthetic signal change.', 'near_miss_ids': ['P001'], 'narrow_search_rationale': 'SYNTHETIC narrow fixture has one source only.'}
    save('gaps/A001.json', {'axis_id': 'A001', 'axis': 'Synthetic signal stability', 'what_has_been_done': 'Synthetic filter [P001].', 'gaps': [gap], 'search': search, 'supports': [support], 'outcome': 'grounded', 'reason': 'Synthetic fixture.'})
    save('candidates/C001.json', {'candidate_id': 'C001', 'axis_id': 'A001', 'gap_id': 'G001', 'prior_candidate': None, 'revision': 0, 'Intuition': 'Adapt the synthetic filter to a changing signal.', 'Gap it attacks': 'Synthetic stability assumption.', 'Source inspiration': 'Synthetic filter [P001].', 'How it maps to this problem': 'Signal corresponds to the changing input.', 'Why it could work / feasibility': 'Stable windows may satisfy the synthetic condition [P001].', 'Novelty vs. closest in-domain work': 'Synthetic comparison extends the stable case [P001].', 'Main risk': 'No stable window exists.', 'novelty_type': 'reinforcing-a-weak-connection', 'source_ids': ['P001'], 'closest_in_domain_ids': ['P001'], 'search': search, 'supports': [support]})
    save('reviews/C001.json', {'candidate_id': 'C001', 'verdict': 'survive', 'focus': None, 'reason': 'Synthetic structural verdict only.', 'strongest_objection': 'Synthetic assumption may fail.', 'checks': {key: 'SYNTHETIC fixture rationale.' for key in ['novelty', 'coherence', 'feasibility', 'clarity', 'mapping', 'grounding', 'methodological_contribution']}, 'search': search, 'supports': [support]})
    save('baselines/G001.json', {'axis_id': 'A001', 'gap_id': 'G001', 'frozen': True, 'proposal_exposed': False, 'before_candidate': 'C001', 'input_files': ['problem.md', 'gaps/A001.json', 'papers/P001.json'], 'input_paper_ids': ['P001'], 'mechanisms': [{'mechanism': 'Synthetic filter [P001].', 'derivation': 'Synthetic derivation from a stable signal.'}], 'supports': [support]})
    report = {'title': 'SYNTHETIC offline proposal', 'topic_relevance': {'sub_topic': ['Synthetic signal'], 'primary_focus': ['Stability']}, 'one_sentence_thesis': 'A synthetic filter may adapt to changing signals.', 'core_problem': {'problem_statement': 'Synthetic assumptions require stable signals [P001].', 'why_it_matters': ['Synthetic users see changing inputs.'], 'concrete_example': 'A synthetic signal changes halfway through a window.'}, 'key_novelty': {'main_idea': 'Synthetic adaptive filter', 'explanation': ['Use stable local windows.', 'Adapt between windows.']}, 'problem_definition': {'formal_setting': 'Synthetic sequential scalar input.', 'inputs': 'Synthetic signal.', 'outputs': 'Synthetic filtered signal.'}, 'key_terms': {'window': 'A local synthetic interval.'}, 'related_work': [{'sub_area': 'Synthetic filters', 'what_it_does': 'Assumes stable signals [P001].', 'open_gap': 'Synthetic signal changes.', 'citations': ['P001']}], 'method': {'high_level_flow': ['Segment then filter.'], 'modules': [{'module': 'Synthetic segmenter', 'role': 'Find local windows.', 'model': 'Synthetic rule.', 'inputs': ['Signal'], 'outputs': ['Windows'], 'notes': 'Proposed synthetic design.'}], 'novel_architectural_elements': ['Adaptive segmentation.'], 'pseudocode': 'For each proposed stable window, apply a filter.', 'design_choices': ['Local windows may approximate stability.'], 'theoretical_grounding': 'A synthetic untested stability hypothesis.'}, 'model_details': {'base_model': 'No learned model in this synthetic proposal.', 'training': {'method': 'No training.', 'objective_functions': ['Synthetic consistency criterion.'], 'adaptation': 'No parameter training.', 'key_hyperparameters': {}}}, 'comparison_to_sota': {'related_methods': ['Synthetic stable filter [P001].'], 'key_differences': ['Adds synthetic local windows.']}, 'proposed_evaluation': {'evaluation_setting': 'Proposed synthetic changing signals.', 'benchmarks': [{'name': 'New synthetic signal set.', 'task_type': 'Filtering', 'newly_constructed': True}], 'baselines': ['Synthetic stable filter [P001].'], 'main_metrics': ['Proposed signal consistency.'], 'ablations': ['Remove synthetic segmentation.']}, 'falsifiable_predictions': [{'pillar': 'Local stability', 'prediction': 'Synthetic local windows may preserve consistency.', 'kill_condition': 'Consistency fails despite stable local windows.'}], 'limitations': ['Synthetic test only.', 'No experiment conducted.', 'No actual scientific novelty judgment.']}
    save('report.json', report)
    save('report-evidence.json', {'candidate_id': 'C001', 'supports': [support]})
    paper = json.loads((root / 'papers/P001.json').read_text())
    answer_text = paper['answers'][0]['answer']
    for name in ('gaps/A001.json', 'candidates/C001.json', 'reviews/C001.json', 'baselines/G001.json', 'report-evidence.json'):
        value = json.loads((root / name).read_text())
        for entry in value['supports']:
            entry['answer_text'] = answer_text
        save(name, value)
    gap = json.loads((root / 'gaps/A001.json').read_text())['gaps'][0]
    for name in ('candidates/C001.json', 'baselines/G001.json'):
        value = json.loads((root / name).read_text())
        value['gap_snapshot'] = gap
        save(name, value)
    candidate = json.loads((root / 'candidates/C001.json').read_text())
    review = json.loads((root / 'reviews/C001.json').read_text())
    review['candidate_snapshot'] = candidate
    save('reviews/C001.json', review)
    receipt = json.loads((root / 'report-evidence.json').read_text())
    receipt.update(candidate_snapshot=candidate, report_snapshot=report)
    save('report-evidence.json', receipt)
    return root
