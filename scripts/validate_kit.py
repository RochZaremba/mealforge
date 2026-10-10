#!/usr/bin/env python3
"""Validate a MealForge agent specification kit (NOT application test suite).

Only Python 3.11+ standard-library required. Optional PyYAML/jsonschema are used
when available, and skipped explicitly otherwise.
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []
checks = []
warnings = []


def must(condition: bool, msg: str) -> None:
    if condition:
        checks.append(msg)
    else:
        errors.append(msg)


required = [
    'README.md','AGENTS.md','MASTER_PROMPT.md','PROMPT_START.txt',
    '.codex/config.toml','docs/PRD.md','docs/RECIPE_SOURCES.md',
    'docs/MEAL_PREP_AND_FOOD_SAFETY.md','docs/AGENT_WORKFLOW.md',
    'docs/NUTRITION_ENGINE.md','docs/OPTIMIZER_SPEC.md',
    'docs/IMPLEMENTATION_STATUS.md','docs/TEST_REPORT.md',
    'docs/REFERENCES.md','docs/DECISIONS.md',
    'contracts/openapi.yaml', 'contracts/recipe-import.schema.json',
    'contracts/nutrition-profile.schema.json',
    'config/recipe_sources.json',
    'fixtures/imports/sample_schema_org_recipe.json',
    'fixtures/imports/link_only_preview.json',
    '.github/workflows/kit-check.yml', 'compose.dev.yml',
]
for path in required:
    must((ROOT/path).is_file(),f'file exists {path}')

adrs=sorted((ROOT/'docs/ADR').glob('*.md'))
for n in range(1,13):
    must(any(x.name.startswith(f'{n:04d}-') for x in adrs),f'ADR-{n:04d} exists')

for n in range(8):
    must((ROOT/f'tasks/WAVE-{n:02d}.md').is_file(),f'WAVE-{n:02d} exists')

try:
    conf=tomllib.loads((ROOT/'.codex/config.toml').read_text(encoding='utf-8'))
    must(conf.get('agents',{}).get('enabled') is True,'Codex subagents enabled')
except Exception as exc:
    errors.append(f'Invalid Codex config: {exc}')

roles=sorted((ROOT/'.codex/agents').glob('*.toml'))
must(len(roles)>=7,'at least seven agent roles')
for role in roles:
    try:
        data=tomllib.loads(role.read_text(encoding='utf-8'))
        must(all(data.get(k) for k in ('name','description','developer_instructions')),f'role valid {role.name}')
        must(data.get('name')==role.stem,f'role filename matches name {role.name}')
    except Exception as exc:
        errors.append(f'Invalid role {role.name}: {exc}')

json_files=sorted(ROOT.rglob('*.json'))
parsed={}
for path in json_files:
    try:
        parsed[path.relative_to(ROOT).as_posix()]=json.loads(path.read_text(encoding='utf-8'))
        checks.append('valid JSON '+path.relative_to(ROOT).as_posix())
    except Exception as exc:
        errors.append(f'Invalid JSON {path.relative_to(ROOT)}: {exc}')

registry=parsed.get('config/recipe_sources.json',{})
if registry:
    must(registry.get('default_mode')=='link_only','registry denies unknown sites')
    must(registry.get('default_automatic_fetch') is False,'registry fetch disabled default')
    items=registry.get('sources',[])
    keys={x.get('id'):x for x in items}
    must(len(keys)==len(items),'source IDs unique')
    for sid in ('mealime','aniagotuje','kwestiasmaku'):
        x=keys.get(sid,{})
        must(x.get('access_mode')=='link_only' and x.get('automatic_fetch_enabled') is False,f'{sid} deny automated scraping')
    for x in items:
        must(x.get('automatic_fetch_enabled') is False,f'{x.get("id")} not auto-fetch enabled at bootstrap')
        must(bool(x.get('domains')) and bool(x.get('license')),f'{x.get("id")} has domains and rights status')

for code in ['MEALIME','ANIAGOTUJE','KWESTIASMAKU']:
    must(code.lower() in (ROOT/'docs/RECIPE_SOURCES.md').read_text(encoding='utf-8').lower(),f'recipe docs mention {code}')

try:
    import yaml
except ImportError:
    warnings.append('PyYAML unavailable: skipped structural YAML validation (CI should install it)')
else:
    for name in ['contracts/openapi.yaml','compose.dev.yml','.github/workflows/kit-check.yml']:
        try:
            obj=yaml.safe_load((ROOT/name).read_text(encoding='utf-8'))
            must(isinstance(obj,dict), f'YAML parsed {name}')
            if name=='contracts/openapi.yaml':
                must(obj.get('openapi')=='3.1.0', 'OpenAPI 3.1 is selected')
        except Exception as exc:
            errors.append(f'Invalid YAML {name}: {exc}')

try:
    import jsonschema
except ImportError:
    warnings.append('jsonschema unavailable: skipped fixture/schema validation (CI should install it)')
else:
    for name in ['contracts/recipe-import.schema.json','contracts/nutrition-profile.schema.json']:
        try:
            jsonschema.Draft202012Validator.check_schema(parsed[name])
            checks.append('valid JSON schema '+name)
        except Exception as exc:
            errors.append(f'Invalid JSON schema {name}: {exc}')
    try:
        jsonschema.validate(parsed['fixtures/imports/link_only_preview.json'],parsed['contracts/recipe-import.schema.json'])
        checks.append('link-only fixture validates against recipe import schema')
    except Exception as exc:
        errors.append(f'Invalid link-only fixture: {exc}')

# Check local links in key markdown indexes only (avoid URL/anchor complexities).
for name in ['README.md','docs/DECISIONS.md','tasks/README.md']:
    content=(ROOT/name).read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',content):
        if target.startswith(('https://','http://','#','mailto:')):
            continue
        path=(ROOT/name).parent/target.split('#',1)[0]
        must(path.exists(),f'{name} local link {target} resolves')

print(f'MealForge SPEC kit checks: {len(checks)} passed / {len(errors)} failed / {len(warnings)} skipped')
for w in warnings:
    print('SKIP:',w)
for e in errors:
    print('FAIL:',e)
if not errors:
    print('PASS: agent kit integrity. NOTE: application/backend/web tests are NOT included at this stage.')
sys.exit(1 if errors else 0)
