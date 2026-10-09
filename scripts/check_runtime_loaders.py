#!/usr/bin/env python3
"""Load adapters with installed runtimes without model calls or saved settings."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, env=None, cwd=None):
    result = subprocess.run(args, env=env, cwd=cwd, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f'{args[0]} exited {result.returncode}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def check_codex():
    with tempfile.TemporaryDirectory(prefix='ideascientist-codex-loader-') as home:
        env = dict(os.environ, CODEX_HOME=home)
        run(['codex', 'plugin', 'marketplace', 'add', str(ROOT)], env=env)
        installed = json.loads(run(['codex', 'plugin', 'add', 'ideascientist@ideascientist-native', '--json'], env=env))
        inventory = json.loads(run(['codex', 'plugin', 'list', '--marketplace', 'ideascientist-native', '--json'], env=env))
        path = Path(installed['installedPath'])
        skills = sorted(p.parent.name for p in (path / 'adapters/codex/skills').glob('*/SKILL.md'))
        expected = sorted(f'ideascientist-{name}' for name in ('ideate', 'resume', 'check', 'evaluate'))
        if skills != expected or not inventory['installed'][0]['enabled']:
            raise RuntimeError('Codex installed component inventory differs')
        for resource in ('references/roles/paper-reader.md', 'references/artifacts.schema.json', 'scripts/check_artifacts.py'):
            if not (path / resource).is_file():
                raise RuntimeError(f'Codex cache is missing {resource}')
        return {'runtime': 'Codex', 'version': run(['codex', '--version']).strip(), 'skills': skills, 'status': 'loaded'}


def check_pi(package, transport=False):
    loader = package / 'dist/core/extensions/loader.js'
    extension = ROOT / ('tests/pi_transport.ts' if transport else 'adapters/pi/index.ts')
    script = '''
const {loadExtensions} = await import(process.argv[1]);
const result = await loadExtensions([process.argv[2]], process.argv[3]);
if (result.errors.length) throw new Error(JSON.stringify(result.errors));
const extension = result.extensions[0];
if (process.argv[4] === "transport") await extension.commands.get("test-ideascientist-transport").handler("", {modelRegistry:{}, ui:{notify:()=>{}}});
console.log(JSON.stringify({runtime:"Pi", tools:[...extension.tools.keys()], commands:[...extension.commands.keys()], status:process.argv[4] === "transport" ? "transport passed" : "loaded"}));
'''
    return json.loads(run(['node', '--input-type=module', '-e', script, str(loader), str(extension), str(ROOT), 'transport' if transport else 'loader']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', action='store_true')
    parser.add_argument('--pi-package', type=Path, help='Installed @earendil-works/pi-coding-agent package directory')
    parser.add_argument('--transport', action='store_true', help='Run deterministic native Pi Agent transport regressions, without authentication')
    args = parser.parse_args()
    if not args.codex and not args.pi_package:
        parser.error('Select --codex or --pi-package')
    if args.codex:
        print(json.dumps(check_codex()))
    if args.pi_package:
        print(json.dumps(check_pi(args.pi_package)))
        if args.transport:
            print(json.dumps(check_pi(args.pi_package, transport=True)))
