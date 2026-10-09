#!/usr/bin/env python3
"""Validate native run artifacts offline. Does not run agents or retrieve papers."""

import argparse
import datetime as dt
import json
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'references/artifacts.schema.json'
STAGES = ('planned', 'gaps', 'candidate', 'review', 'report', 'evaluated')
PAPER_ID = re.compile(r'^P[0-9]{3,}$')


def validate_schema(value, schema, definitions, path='$'):
    if '$ref' in schema:
        return validate_schema(value, definitions[schema['$ref'].split('/')[-1]], definitions, path)
    if 'anyOf' in schema:
        branches = [validate_schema(value, branch, definitions, path) for branch in schema['anyOf']]
        return [] if any(not errors for errors in branches) else [f'{path}: no allowed type matches']
    errors = []
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        errors.append(f'{path}: expected constant {schema["const"]!r}')
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: expected one of {schema["enum"]}')
    kind = schema.get('type')
    matches = {
        'object': isinstance(value, dict), 'array': isinstance(value, list),
        'string': isinstance(value, str), 'integer': type(value) is int,
        'number': type(value) in (int, float), 'boolean': type(value) is bool,
        'null': value is None,
    }
    if kind and not matches[kind]:
        return errors + [f'{path}: expected {kind}']
    if kind == 'object':
        properties = schema.get('properties', {})
        for key in schema.get('required', []):
            if key not in value:
                errors.append(f'{path}.{key}: required')
        if len(value) < schema.get('minProperties', 0):
            errors.append(f'{path}: too few properties')
        for key, child in value.items():
            child_schema = properties.get(key, schema.get('additionalProperties', True))
            if child_schema is False:
                errors.append(f'{path}.{key}: unknown field')
            elif isinstance(child_schema, dict):
                errors.extend(validate_schema(child, child_schema, definitions, f'{path}.{key}'))
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', float('inf')):
            errors.append(f'{path}: invalid item count')
        for index, child in enumerate(value):
            errors.extend(validate_schema(child, schema['items'], definitions, f'{path}[{index}]'))
    elif kind == 'string':
        if len(value.strip()) < schema.get('minLength', 0):
            errors.append(f'{path}: substantive text required')
        if 'pattern' in schema and not re.fullmatch(schema['pattern'], value):
            errors.append(f'{path}: invalid identifier or value')
        if schema.get('format') == 'date':
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError
                dt.date.fromisoformat(value)
            except ValueError:
                errors.append(f'{path}: expected valid YYYY-MM-DD')
    elif kind in ('integer', 'number'):
        if not schema.get('minimum', -float('inf')) <= value <= schema.get('maximum', float('inf')):
            errors.append(f'{path}: out of range')
    return errors


def cited_ids(value):
    ids, errors = set(), []
    if isinstance(value, str):
        for match in re.finditer(r'(?P<identifier>\b[A-Za-z_]\w*)?\[(?P<bracket>[^\]\n]+)\]', value):
            bracket = match['bracket']
            if bracket.startswith('P') or (bracket.isdigit() and match['identifier'] is None):
                if not PAPER_ID.fullmatch(bracket):
                    errors.append(f'invalid citation [{bracket}]; use one stable P ID per bracket')
                else:
                    ids.add(bracket)
    elif isinstance(value, dict):
        for key, child in value.items():
            if key in ('paper_id', 'citations', 'near_miss_ids', 'source_ids', 'closest_in_domain_ids', 'input_paper_ids'):
                ids.update([child] if isinstance(child, str) else child)
            child_ids, child_errors = cited_ids(child)
            ids.update(child_ids)
            errors.extend(child_errors)
    elif isinstance(value, list):
        for child in value:
            child_ids, child_errors = cited_ids(child)
            ids.update(child_ids)
            errors.extend(child_errors)
    return ids, errors


def check_run(run_dir):
    root = Path(run_dir).resolve()
    definitions = json.loads(SCHEMA_PATH.read_text())['$defs']
    errors, artifacts = [], {}

    def load(path, kind, required=False):
        full = root / path
        if not full.is_file():
            if required:
                errors.append(f'{path}: missing artifact')
            return None
        try:
            data = json.loads(full.read_text())
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f'{path}: cannot read JSON: {exc}')
            return None
        issues = validate_schema(data, definitions[kind], definitions, str(path))
        errors.extend(issues)
        if issues:
            return None
        artifacts[str(path)] = data
        return data

    run = load('run.json', 'run', True)
    if run is None:
        return errors
    if not (root / 'plan.md').is_file():
        errors.append('plan.md: missing coordinator plan')
    if root.name != run['slug']:
        errors.append('run.json: slug must match run directory name')
    for name, budget in run['budgets'].items():
        if budget['spent'] > budget['limit']:
            errors.append(f'budgets.{name}: spent exceeds limit')
    if run['status'] == 'complete' and run['stage'] not in ('report', 'evaluated'):
        errors.append('run.json: complete requires a report')

    def date_check(identity, label):
        cutoff = run['cutoff']
        if cutoff and (identity['publication_date'] is None or identity['publication_date'] > cutoff):
            errors.append(f'{label}: exact source version date unknown or after cutoff')

    registry = {}
    identities = set()
    for paper in run['papers']:
        pid, identity = paper['paper_id'], paper['identity']
        if pid in registry:
            errors.append(f'{pid}: duplicate registered ID')
        key = (identity['doi'] or identity['url'], identity['version'])
        if key in identities:
            errors.append(f'{pid}: duplicate bibliographic version; reuse its ID')
        identities.add(key)
        registry[pid] = identity
        date_check(identity, pid)
    papers = {}
    for path in sorted((root / 'papers').glob('*.json')):
        paper = load(path.relative_to(root), 'paper')
        if paper is None:
            continue
        pid = paper['paper_id']
        if path.stem != pid or registry.get(pid) != paper['identity']:
            errors.append(f'{path.name}: digest identity does not match registration')
        papers[pid] = paper
        date_check(paper['identity'], path.name)
        if paper['read_status'] == 'read' and paper['access_level'] == 'unavailable':
            errors.append(f'{pid}: unavailable source cannot be read')
        goals = [answer['goal'] for answer in paper['answers']]
        if len(goals) != len(set(goals)):
            errors.append(f'{pid}: duplicate cumulative reading goal')
        for answer in paper['answers']:
            if answer['status'] == 'answered':
                if not answer['locator'] or answer['access_level'] == 'unavailable':
                    errors.append(f'{pid}: answered goal needs an access level and locator')
                if answer['access_level'] == 'full_text' and paper['access_level'] != 'full_text':
                    errors.append(f'{pid}: full-text answer exceeds source access')
                if answer['access_level'] == 'abstract' and answer['locator'] != 'Abstract':
                    errors.append(f'{pid}: abstract answer must locate Abstract')

    def evidence(label, value, supports):
        ids, issues = cited_ids(value)
        errors.extend(f'{label}: {issue}' for issue in issues)
        supported = set()
        for support in supports:
            pid = support['paper_id']
            paper = papers.get(pid)
            if not paper or paper['read_status'] != 'read':
                errors.append(f'{label}: support {pid} has no actual read digest')
                continue
            answer = next((a for a in paper['answers'] if a['goal'] == support['goal'] and a['locator'] == support['locator'] and a['status'] == 'answered'), None)
            if answer is None:
                errors.append(f'{label}: support {pid} does not match an answered goal and locator')
            elif answer['answer'] != support['answer_text']:
                errors.append(f'{label}: support {pid} answer changed since receipt')
            elif support['kind'] == 'mechanism' and answer['access_level'] != 'full_text':
                errors.append(f'{label}: abstract-only support cannot back mechanism assertions for {pid}')
            else:
                supported.add(pid)
        for pid in ids:
            if pid not in registry or pid not in papers or papers[pid]['read_status'] != 'read':
                errors.append(f'{label}: cited {pid} has no registered read digest')
            if pid not in supported:
                errors.append(f'{label}: cited {pid} lacks explicit support locator')

    axis_names = {a['axis_id']: a['name'] for a in run['axes']}
    if len(axis_names) != len(run['axes']):
        errors.append('run.json: duplicate axis ID')
    axes, gaps, candidates, reviews, baselines = {}, {}, {}, {}, {}
    groups = (('gaps', 'gaps', axes, 'axis_id'), ('candidates', 'candidate', candidates, 'candidate_id'), ('reviews', 'review', reviews, 'candidate_id'), ('baselines', 'baseline', baselines, 'gap_id'))
    for directory, kind, collection, key in groups:
        for path in sorted((root / directory).glob('*.json')):
            value = load(path.relative_to(root), kind)
            if value is None:
                continue
            if path.stem != value[key] or value[key] in collection:
                errors.append(f'{path}: file ID mismatch or duplicate artifact')
            collection[value[key]] = value
            evidence(str(path.relative_to(root)), value, value['supports'])
    for aid, axis in axes.items():
        if axis_names.get(aid) != axis['axis']:
            errors.append(f'{aid}: must reproduce exactly one assigned axis')
        if axis['outcome'] in ('no_gap', 'blocked') and axis['gaps']:
            errors.append(f'{aid}: no_gap or blocked cannot publish grounded gaps')
        if axis['outcome'] == 'grounded' and not axis['gaps']:
            errors.append(f'{aid}: zero gaps must be recorded as no_gap or blocked')
        for gap in axis['gaps']:
            gid = gap['gap_id']
            if gid in gaps:
                errors.append(f'{gid}: duplicate gap ID')
            gaps[gid] = (aid, gap)
            if len(set(gap['near_miss_ids'])) < 2 and not gap['narrow_search_rationale']:
                errors.append(f'{gid}: fewer than two near misses needs narrow search rationale')
            for pid in gap['near_miss_ids']:
                if not any(s['paper_id'] == pid and s['kind'] == 'mechanism' for s in axis['supports']):
                    errors.append(f'{gid}: near-miss deficiency requires full-text mechanism support')
    per_gap = {}
    for cid, candidate in candidates.items():
        gid, aid = candidate['gap_id'], candidate['axis_id']
        if gid not in gaps or gaps[gid][0] != aid:
            errors.append(f'{cid}: candidate must attack one existing gap on its axis')
        if gid in gaps and candidate['gap_snapshot'] != gaps[gid][1]:
            errors.append(f'{cid}: gap changed since candidate creation')
        per_gap[gid] = per_gap.get(gid, 0) + 1
        if candidate['revision'] > run['max_revisions']:
            errors.append(f'{cid}: revision budget exceeded')
        prior = candidate['prior_candidate']
        if prior:
            parent, review = candidates.get(prior), reviews.get(prior)
            if not parent or parent['gap_id'] != gid or candidate['revision'] != parent['revision'] + 1 or int(cid[1:]) <= int(prior[1:]):
                errors.append(f'{cid}: revision requires a new ID and same-gap predecessor')
            if not review or review['verdict'] != 'revise':
                errors.append(f'{cid}: revision requires a revise verdict on its predecessor')
        elif candidate['revision'] != 0:
            errors.append(f'{cid}: initial candidate has revision zero')
        for pid in candidate['source_ids'] + candidate['closest_in_domain_ids']:
            if not any(s['paper_id'] == pid and s['kind'] == 'mechanism' for s in candidate['supports']):
                errors.append(f'{cid}: source and closest work need mechanism support')
        if run['blind_baseline'] and gid not in baselines:
            errors.append(f'{cid}: enabled blind baseline must freeze before candidate')
    for gid, count in per_gap.items():
        if count > run['max_candidates_per_gap']:
            errors.append(f'{gid}: candidate and pivot budget exceeded')
    for cid, review in reviews.items():
        if cid not in candidates:
            errors.append(f'{cid}: review target missing')
        if cid in candidates and review['candidate_snapshot'] != candidates[cid]:
            errors.append(f'{cid}: candidate changed since review')
        if (review['verdict'] == 'revise') != (review['focus'] is not None):
            errors.append(f'{cid}: only revise verdict requires one focus')
        if review['verdict'] in ('survive', 'revise', 'reject') and review['search']['status'] != 'searched':
            errors.append(f'{cid}: verified verdict requires active disconfirming search')
    for gid, baseline in baselines.items():
        if gid not in gaps or gaps[gid][0] != baseline['axis_id']:
            errors.append(f'{gid}: baseline needs the assigned gap')
        if gid in gaps and baseline['gap_snapshot'] != gaps[gid][1]:
            errors.append(f'{gid}: gap changed since baseline freeze')
        if any(not (p == 'problem.md' or p == f'gaps/{baseline["axis_id"]}.json' or re.fullmatch(r'papers/P[0-9]{3,}\.json', p)) for p in baseline['input_files']):
            errors.append(f'{gid}: baseline inputs must be proposal-blind allowlist')
        expected_inputs = {'problem.md', f'gaps/{baseline["axis_id"]}.json'} | {f'papers/{pid}.json' for pid in baseline['input_paper_ids']}
        if set(baseline['input_files']) != expected_inputs or any(not (root / p).is_file() for p in baseline['input_files']):
            errors.append(f'{gid}: blind baseline input metadata must resolve exactly')
        if gid in gaps and not set(baseline['input_paper_ids']).issubset(gaps[gid][1]['near_miss_ids']):
            errors.append(f'{gid}: baseline may see only problem and near-miss digests')
        for cid, candidate in candidates.items():
            if candidate['gap_id'] == gid and int(baseline['before_candidate'][1:]) > int(cid[1:]):
                errors.append(f'{gid}: baseline freeze marker is after candidate exposure')

    for path in sorted((root / 'discoveries').glob('*.json')):
        discovery = load(path.relative_to(root), 'discovery')
        if discovery:
            if path.stem != discovery['task_id']:
                errors.append(f'{path.name}: discovery task ID mismatch')
            if not discovery['sources']:
                matching = [task for task in run['tasks'] if task['task_id'] == discovery['task_id']]
                if len(matching) != 1 or matching[0]['status'] != 'blocked' or matching[0]['role'] != discovery['role'] or matching[0]['output'] != str(path.relative_to(root)):
                    errors.append(f'{path.name}: empty blocked discovery requires matching blocked task, role, and output')
            for source in discovery['sources']:
                date_check(source['identity'], path.name)
    selected = run['selected']
    aid, gid, cid = (selected[k] for k in ('axis_id', 'gap_id', 'candidate_id'))
    stage = STAGES.index(run['stage'])
    if aid is not None and aid not in axis_names:
        errors.append('selected.axis_id: unknown assigned axis')
    if gid is not None and (gid not in gaps or gaps[gid][0] != aid):
        errors.append('selected.gap_id: missing gap or wrong selected axis')
    if cid is not None and (cid not in candidates or candidates[cid]['gap_id'] != gid):
        errors.append('selected.candidate_id: missing candidate or wrong selected gap')
    if stage >= 1 and aid not in axes:
        errors.append('stage gaps: selected axis output required')
    if stage >= 2 and cid not in candidates:
        errors.append('stage candidate: selected candidate required')
    if stage >= 3 and cid not in reviews:
        errors.append('stage review: selected current candidate must be reviewed')
    if run['status'] == 'no_gap' and (stage != 1 or aid not in axes or axes[aid]['gaps'] or cid is not None):
        errors.append('no_gap: requires zero-gap axis and no selected candidate')
    report = load('report.json', 'report', stage >= 4)
    receipt = load('report-evidence.json', 'report_evidence', report is not None or stage >= 4)
    if report is not None:
        if not cid or cid not in reviews or reviews[cid]['verdict'] != 'survive':
            errors.append('report.json: selected current candidate needs survive verdict')
        if receipt is not None:
            if receipt['candidate_id'] != cid:
                errors.append('report-evidence.json: target is not selected current candidate')
            if cid in candidates and receipt['candidate_snapshot'] != candidates[cid]:
                errors.append('report-evidence.json: candidate changed since report')
            if receipt['report_snapshot'] != report:
                errors.append('report-evidence.json: report changed since evidence receipt')
            evidence('report.json', report, receipt['supports'])
            evidence('report-evidence.json', receipt, receipt['supports'])
    evaluation = load('evaluation.json', 'evaluation', stage >= 5)
    if evaluation:
        if report is None or evaluation['candidate_id'] != cid:
            errors.append('evaluation.json: requires report of selected current candidate')
        evidence('evaluation.json', evaluation, evaluation['supports'])
        if evaluation['novelty']['scope'] != ('cutoff' if run['cutoff'] else 'live'):
            errors.append('evaluation.json: novelty scope must match run cutoff')
        novelty = evaluation['nonobviousness']
        expected_baseline = f'baselines/{gid}.json'
        if novelty['status'] == 'compared' and (gid not in baselines or novelty['baseline_file'] != expected_baseline):
            errors.append('evaluation.json: nonobviousness needs frozen proposal-blind baseline')
        reference = evaluation['reference']
        if reference['status'] == 'unavailable' and any(reference[k] is not None for k in ('file', 'match', 'citation_f1')):
            errors.append('evaluation.json: unavailable reference metrics must be null, never fake zero')
        if reference['status'] == 'user_supplied' and (not reference['file'] or not Path(reference['file']).is_file() or reference['match'] is None or reference['citation_f1'] is None):
            errors.append('evaluation.json: user-supplied reference must resolve and have comparison')
    task_ids, active = set(), 0
    outputs = set()
    for task in run['tasks']:
        tid = task['task_id']
        if tid in task_ids:
            errors.append(f'{tid}: duplicate task ID')
        task_ids.add(tid)
        output = Path(task['output'])
        if output.is_absolute() or '..' in output.parts:
            errors.append(f'{tid}: task output must stay in run directory')
        if task['status'] == 'active':
            active += 1
            if task['output'] in outputs:
                errors.append(f'{tid}: concurrent shared output ownership')
            outputs.add(task['output'])
        if task['status'] == 'done' and not (root / output).is_file():
            errors.append(f'{tid}: done task has missing output')
    if active > 1:
        errors.append('tasks: sequential dispatch requires at most one active task')
    for name, collection in (('paper', registry), ('gap', gaps), ('candidate', candidates), ('task', task_ids)):
        if collection and run['next_ids'][name] <= max(int(key[1:]) for key in collection):
            errors.append(f'next_ids.{name}: must exceed all allocated IDs')
    all_supports = [support for value in artifacts.values() for support in value.get('supports', [])]
    for path in root.rglob('*.md'):
        evidence(str(path.relative_to(root)), path.read_text(), all_supports)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    errors = check_run(args.run_dir)
    if args.json:
        print(json.dumps({'ok': not errors, 'errors': errors}, ensure_ascii=False, indent=2))
    elif errors:
        print('\n'.join(errors))
    else:
        print('Artifact contracts and evidence receipts pass. Semantic support and chronology require review.')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
