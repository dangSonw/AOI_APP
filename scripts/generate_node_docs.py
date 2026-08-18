import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NODES_ROOT = PROJECT_ROOT / 'core' / 'nodes'


def display_value(value: object) -> str:
    if value is None:
        return '—'
    if isinstance(value, bool):
        return '`true`' if value else '`false`'
    if isinstance(value, (dict, list)):
        return f'`{json.dumps(value, ensure_ascii=False)}`'
    return f'`{value}`'


def parameter_rows(parameters: list[dict], guidance: dict[str, str], *, vietnamese: bool) -> str:
    if not parameters:
        return '| — | — | — | — | — | — | Node không có tham số cấu hình. |' if vietnamese else '| — | — | — | — | — | — | Node has no configurable parameters. |'
    return '\n'.join(
        '| `{key}` | `{kind}` | {default} | {minimum} | {maximum} | {options} | {meaning} |'.format(
            key=parameter['key'], kind=parameter['kind'], default=display_value(parameter.get('default_value')),
            minimum=display_value(parameter.get('minimum')), maximum=display_value(parameter.get('maximum')),
            options=', '.join(display_value(value) for value in parameter.get('options', [])) or '—',
            meaning=guidance.get(parameter['key']) or parameter.get('description') or parameter['label'],
        ) for parameter in parameters
    )


def port_rows(ports: list[dict], *, vietnamese: bool) -> str:
    return '\n'.join(
        '| `{key}` | {direction} | `{data_type}` | {required} | {variadic} | {label} |'.format(
            key=port['key'], direction=('đầu vào' if port['direction'] == 'input' else 'đầu ra') if vietnamese else port['direction'],
            data_type=port['data_type'], required=('có' if port.get('required', True) else 'không') if vietnamese else ('yes' if port.get('required', True) else 'no'),
            variadic=('có' if port.get('variadic', False) else 'không') if vietnamese else ('yes' if port.get('variadic', False) else 'no'), label=port['label'],
        ) for port in ports
    ) or ('| — | — | — | — | — | Không có port |' if vietnamese else '| — | — | — | — | — | No ports |')


def bullets(values: list[str]) -> str:
    return '\n'.join(f'- {value}' for value in values)


def chain(values: list[str]) -> str:
    return ' → '.join(f'`{value}`' for value in values)


def troubleshooting(values: list[dict[str, str]], *, vietnamese: bool) -> str:
    header = '| Hiện tượng | Nguyên nhân | Cách xử lý |\n|---|---|---|' if vietnamese else '| Symptom | Cause | Resolution |\n|---|---|---|'
    return header + '\n' + '\n'.join(f"| {item['symptom']} | {item['cause']} | {item['resolution']} |" for item in values)


def render(manifest: dict, documentation: dict, language: str) -> str:
    vi = language == 'vi'
    definition, content = manifest['definition'], documentation[language]
    inputs, outputs, parameters = definition.get('inputs', []), definition.get('outputs', []), definition.get('parameters', [])
    capabilities = ', '.join(f'`{item}`' for item in manifest.get('capabilities', [])) or ('Chưa khai báo' if vi else 'None declared')
    parameter_json = json.dumps(content['example']['parameters'], ensure_ascii=False, indent=2)
    input_steps = '\n'.join(
        (f"{i}. Nối output `{port['data_type']}` vào `{port['key']}`. " if vi else f"{i}. Connect a `{port['data_type']}` output to `{port['key']}`. ") + content['inputGuidance'].get(port['key'], '')
        for i, port in enumerate(inputs, 1)
    ) or ('Node không yêu cầu input.' if vi else 'This node has no input.')
    output_steps = '\n'.join(f"- `{port['key']}` (`{port['data_type']}`): {content['outputGuidance'].get(port['key'], port['label'])}" for port in outputs) or '- —'
    title = f"Node {definition['name']}" if vi else f"{definition['name']} node"
    debug_notice = '> **Lưu ý DEBUG:** Có thể chạy để phát triển/nghiên cứu, chưa được duyệt production.' if vi else '> **DEBUG notice:** Executable for development/research, not approved for production.'
    return f'''# {title}

## {'Mục đích và cách dùng nhanh' if vi else 'Purpose and quick use'}

{content['overview']}

**{'Dùng khi' if vi else 'Use when'}:** {content['whenToUse']}

**{'Luồng nhanh' if vi else 'Quick flow'}:** {chain(content['example']['workflow'])}

## {'Cấu trúc node' if vi else 'Node structure'}

```text
{', '.join(port['key'] for port in inputs) or '(no input)'}
    │
    ▼
[{manifest['id']}]
    │
    └── {', '.join(port['key'] for port in outputs) or '(no output)'}
```

{content['structure']}

## {'Nguyên lý xử lý' if vi else 'How the algorithm works'}

{bullets(content['algorithm'])}

## {'Contract runtime' if vi else 'Runtime contract'}

| {'Trường' if vi else 'Field'} | {'Giá trị' if vi else 'Value'} |
|---|---|
| Node ID | `{manifest['id']}` |
| {'Nhóm' if vi else 'Category'} | {definition['category']} |
| {'Trạng thái' if vi else 'Status'} | `{manifest['use']}` |
| {'Đích thực thi' if vi else 'Execution target'} | `{manifest['executionTarget']}` |
| {'Khả năng' if vi else 'Capabilities'} | {capabilities} |

{debug_notice}

## {'Cách nhập dữ liệu và đọc output' if vi else 'How to provide inputs and read outputs'}

| Key | {'Hướng' if vi else 'Direction'} | {'Kiểu' if vi else 'Type'} | Required | Variadic | Label |
|---|---|---|---|---|---|
{port_rows([*inputs, *outputs], vietnamese=vi)}

### {'Nhập input' if vi else 'Provide inputs'}

{input_steps}

### {'Đọc output' if vi else 'Read outputs'}

{output_steps}

## {'Cách nhập tham số' if vi else 'How to enter parameters'}

| Key | Kind | Default | Min | Max | Options | {'Cách nhập / Ý nghĩa' if vi else 'How to enter / Meaning'} |
|---|---|---|---|---|---|---|
{parameter_rows(parameters, content['parameterGuidance'], vietnamese=vi)}

## {'Ví dụ sử dụng có thể làm theo ngay' if vi else 'Copy-ready usage example'}

**{'Mục tiêu' if vi else 'Goal'}:** {content['example']['goal']}

**Workflow:** {chain(content['example']['workflow'])}

{bullets(content['example']['steps'])}

**{'Nhập trong bảng config' if vi else 'Paste into the config panel'}:**

```json
{parameter_json}
```

**{'Input ví dụ' if vi else 'Example input'}:** {content['example']['input']}

**{'Kết quả mong đợi' if vi else 'Expected output'}:** {content['example']['expectedOutput']}

## {'Lỗi thường gặp' if vi else 'Troubleshooting'}

{troubleshooting(content['troubleshooting'], vietnamese=vi)}

## {'Giới hạn và kiểm tra trước production' if vi else 'Limitations and production checks'}

{bullets(content['limitations'])}

### {'Checklist trước production' if vi else 'Production checklist'}

{bullets(content['productionChecklist'])}
'''


def render_english(manifest: dict, documentation: dict) -> str:
    return render(manifest, documentation, 'en')


def render_vietnamese(manifest: dict, documentation: dict) -> str:
    return render(manifest, documentation, 'vi')


def main() -> None:
    manifests = sorted(NODES_ROOT.glob('*/*/manifest.json'))
    generated = 0
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        documentation_path = manifest_path.with_name('documentation.json')
        if manifest['use'] == 'debug' and not documentation_path.is_file():
            raise ValueError(f'DEBUG node {manifest["id"]} is missing documentation.json.')
        if not documentation_path.is_file():
            continue
        documentation = json.loads(documentation_path.read_text(encoding='utf-8'))
        with manifest_path.with_name('README.md').open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(render_english(manifest, documentation))
        with manifest_path.with_name('README.md.vn').open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(render_vietnamese(manifest, documentation))
        generated += 1
    print(f'Generated detailed bilingual documentation for {generated} node packages.')


if __name__ == '__main__':
    main()