#!/usr/bin/env python3
"""Check native plugin structure and references without loading an agent runtime."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = {'orchestrator', 'gap-finder', 'innovator', 'reviewer', 'report-writer', 'paper-reader', 'blind-baseline'}
COMMANDS = {'ideate', 'resume', 'evaluate', 'check'}
TOOLS = {
    'orchestrator': {'Read', 'Write', 'Edit', 'Agent'},
    'paper-reader': {'Read', 'Write', 'Edit', 'WebFetch'},
    'blind-baseline': {'Read', 'Write', 'Edit'},
}


def check_plugin(root=ROOT):
    root = Path(root)
    errors = []
    plugin = json.loads((root / '.claude-plugin/plugin.json').read_text())
    market = json.loads((root / '.claude-plugin/marketplace.json').read_text())
    if plugin['name'] != 'ideascientist' or len(market['plugins']) != 1 or market['plugins'][0]['source'] != '.':
        errors.append('manifest: expected one ideascientist plugin rooted at .')
    agents = {p.stem for p in (root / 'agents').glob('*.md')}
    skills = {p.parent.name for p in (root / 'skills').glob('*/SKILL.md')}
    if agents != ROLES or skills != COMMANDS:
        errors.append('components: required native role/command inventory mismatch')
    for file in list((root / 'agents').glob('*.md')) + list((root / 'skills').glob('*/SKILL.md')):
        text = file.read_text()
        match = re.match(r'^---\n(.*?)\n---\n', text, re.S)
        if not match:
            errors.append(f'{file.name}: missing frontmatter')
            continue
        fields = dict(line.split(': ', 1) for line in match[1].splitlines() if ': ' in line)
        if not fields.get('name') or not fields.get('description'):
            errors.append(f'{file.name}: missing name/description')
        if file.parent.name == 'agents':
            expected = TOOLS.get(file.stem, {'Read', 'Write', 'Edit', 'WebSearch', 'Agent'})
            if set(fields.get('tools', '').split(', ')) != expected or fields.get('model') != 'inherit':
                errors.append(f'{file.name}: incorrect native tool boundary or model inheritance')
        elif fields.get('context') == 'fork' or fields.get('disable-model-invocation') != 'true':
            errors.append(f'{file}: commands must run inline and be explicit user invocations')
    for file in list((root / 'agents').glob('*.md')) + list((root / 'skills').glob('*/SKILL.md')) + list((root / 'references').glob('*.md')):
        text = file.read_text()
        for target in re.findall(r'ideascientist:([a-z][a-z-]+)', text):
            if target not in ROLES | COMMANDS:
                errors.append(f'{file.name}: unknown native target {target}')
        for resource in re.findall(r'`(?:\$\{CLAUDE_PLUGIN_ROOT\}/)?((?:references|templates|scripts)/[a-zA-Z0-9_./-]+)`', text):
            if not (root / resource).is_file():
                errors.append(f'{file.name}: missing plugin reference {resource}')
    for name in ('ideate', 'resume'):
        if 'references/workflow.md' not in (root / f'skills/{name}/SKILL.md').read_text():
            errors.append(f'{name}: missing shared workflow')
    if 'references/workflow.md' not in (root / 'agents/orchestrator.md').read_text():
        errors.append('orchestrator: missing shared workflow')
    return errors


if __name__ == '__main__':
    failures = check_plugin()
    print('\n'.join(failures) if failures else 'Native plugin structure passes.')
    raise SystemExit(bool(failures))
