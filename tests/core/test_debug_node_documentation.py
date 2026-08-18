import json
import subprocess
import sys
from pathlib import Path


NODES_ROOT = Path('core/nodes')
REQUIRED_LANGUAGE_KEYS = {
    'overview', 'whenToUse', 'structure', 'algorithm', 'inputGuidance', 'outputGuidance',
    'parameterGuidance', 'example', 'troubleshooting', 'limitations', 'productionChecklist',
}


def _debug_packages() -> list[tuple[Path, dict]]:
    packages = []
    for manifest_path in NODES_ROOT.glob('*/*/manifest.json'):
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest['use'] == 'debug':
            packages.append((manifest_path.parent, manifest))
    return packages


def test_every_debug_node_has_structured_bilingual_documentation() -> None:
    packages = _debug_packages()
    assert len(packages) == 79

    for directory, manifest in packages:
        metadata = json.loads((directory / 'documentation.json').read_text(encoding='utf-8'))
        assert metadata['documentationVersion'] == 1
        for language in ('en', 'vi'):
            content = metadata[language]
            assert REQUIRED_LANGUAGE_KEYS <= content.keys()
            assert manifest['id'] in content['overview']
            assert len(content['algorithm']) >= 3
            assert manifest['id'] in content['example']['workflow']
            assert len(content['troubleshooting']) >= 3
            manifest_keys = {item['key'] for item in manifest['definition'].get('parameters', [])}
            assert set(content['parameterGuidance']) == manifest_keys
            assert set(content['example']['parameters']) == manifest_keys


def test_debug_readmes_explain_structure_input_config_example_and_errors() -> None:
    for directory, manifest in _debug_packages():
        english = (directory / 'README.md').read_text(encoding='utf-8')
        vietnamese = (directory / 'README.md.vn').read_text(encoding='utf-8')
        assert manifest['id'] in english and manifest['id'] in vietnamese
        assert '## Node structure' in english
        assert '## Cấu trúc node' in vietnamese
        assert '## How to enter parameters' in english
        assert '## Cách nhập tham số' in vietnamese
        assert '## Copy-ready usage example' in english
        assert '## Ví dụ sử dụng có thể làm theo ngay' in vietnamese
        assert '```json' in english and '```json' in vietnamese
        assert '## Troubleshooting' in english and '## Lỗi thường gặp' in vietnamese


def test_documentation_generation_is_deterministic() -> None:
    paths = [path for directory, _ in _debug_packages() for path in (directory / 'README.md', directory / 'README.md.vn')]
    before = {path: path.read_bytes() for path in paths}

    subprocess.run([sys.executable, 'scripts/generate_node_docs.py'], check=True)

    assert {path: path.read_bytes() for path in paths} == before