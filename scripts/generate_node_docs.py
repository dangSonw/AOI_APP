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


def parameter_rows(parameters: list[dict]) -> str:
    if not parameters:
        return '| — | — | — | — | — | — | No parameters |'
    return '\n'.join(
        '| `{key}` | `{kind}` | {default} | {minimum} | {maximum} | {options} | {meaning} |'.format(
            key=parameter['key'],
            kind=parameter['kind'],
            default=display_value(parameter.get('default_value')),
            minimum=display_value(parameter.get('minimum')),
            maximum=display_value(parameter.get('maximum')),
            options=', '.join(display_value(value) for value in parameter.get('options', [])) or '—',
            meaning=parameter.get('description') or parameter['label'],
        )
        for parameter in parameters
    )


def port_rows(ports: list[dict], *, vietnamese: bool = False) -> str:
    if not ports:
        return '| — | — | — | — | — | Không có port |' if vietnamese else '| — | — | — | — | — | No ports |'
    return '\n'.join(
        '| `{key}` | {direction} | `{data_type}` | {required} | {variadic} | {label} |'.format(
            key=port['key'],
            direction=('đầu vào' if port['direction'] == 'input' else 'đầu ra') if vietnamese else port['direction'],
            data_type=port['data_type'],
            required=('có' if port.get('required', True) else 'không') if vietnamese else ('yes' if port.get('required', True) else 'no'),
            variadic=('có' if port.get('variadic', False) else 'không') if vietnamese else ('yes' if port.get('variadic', False) else 'no'),
            label=port['label'],
        )
        for port in ports
    )


def runtime_notice(status: str, *, vietnamese: bool = False) -> str:
    if vietnamese:
        if status == 'debug':
            return 'Runtime `debug` có thể thực thi trong phát triển, mô phỏng và nghiên cứu. Node chưa được duyệt cho production.'
        return 'Runtime `test` mới có contract. Khi chạy, node phát sinh `NodeNotImplementedError`; không dùng trong workflow cần hoàn thành.'
    if status == 'debug':
        return 'Executable `debug` runtime for development, simulation, and research. This node is not approved for production.'
    return 'Contract-only `test` runtime. Execution raises `NodeNotImplementedError`; do not use it in a workflow expected to complete.'


def render_english(manifest: dict) -> str:
    definition = manifest['definition']
    inputs = definition.get('inputs', [])
    outputs = definition.get('outputs', [])
    capabilities = ', '.join(f'`{item}`' for item in manifest.get('capabilities', [])) or 'None declared'
    input_keys = ', '.join(f"`{port['key']}`" for port in inputs) or 'none'
    output_keys = ', '.join(f"`{port['key']}`" for port in outputs) or 'none'
    return f'''# {definition['name']} node

## Purpose

{definition['description']}

## Runtime contract

| Field | Value |
|---|---|
| Node ID | `{manifest['id']}` |
| Category | {definition['category']} |
| Status | `{manifest['use']}` |
| Package version | `{manifest['packageVersion']}` |
| Execution target | `{manifest['executionTarget']}` |
| Inspector | `{manifest['inspector']['kind']}` |
| Capabilities | {capabilities} |

{runtime_notice(manifest['use'])}

## Ports

| Key | Direction | Data type | Required | Variadic | Label |
|---|---|---|---|---|---|
{port_rows([*inputs, *outputs])}

## Parameters

| Key | Kind | Default | Minimum | Maximum | Options | Meaning |
|---|---|---|---|---|---|---|
{parameter_rows(definition.get('parameters', []))}

## Workflow use

1. Add **{definition['name']}** from **{definition['category']}** in Workflow editor.
2. Connect typed inputs: {input_keys}.
3. Configure parameters within listed limits.
4. Connect outputs: {output_keys}.
5. Save workflow before pressing **Run** in Project workspace.

Connections require exact data-type equality. Workflow remains a DAG; cycles and self-loops are rejected. `delay` and `bounded-repeat` provide bounded behavior without graph cycles.

## Evidence and safety

Runtime stores parameters, summarized inputs and outputs, duration, version, status, and evidence hash. Image arrays are not stored in JSON evidence. `image-output` marks latest image for encoded PNG preview in 2D optical view.

- Status `{manifest['use']}` is not production approval.
- Validate dimensions, channel order, dtype, thresholds, timing, and memory on target hardware.
- Production mode rejects every node not marked `release`.
'''


def render_vietnamese(manifest: dict) -> str:
    definition = manifest['definition']
    inputs = definition.get('inputs', [])
    outputs = definition.get('outputs', [])
    capabilities = ', '.join(f'`{item}`' for item in manifest.get('capabilities', [])) or 'Chưa khai báo'
    input_keys = ', '.join(f"`{port['key']}`" for port in inputs) or 'không có'
    output_keys = ', '.join(f"`{port['key']}`" for port in outputs) or 'không có'
    return f'''# Node {definition['name']}

## Mục đích

Node `{manifest['id']}` xử lý bước **{definition['name']}** thuộc nhóm **{definition['category']}** trong workflow AOI. Mô tả contract gốc: “{definition['description']}”

## Contract runtime

| Trường | Giá trị |
|---|---|
| Node ID | `{manifest['id']}` |
| Nhóm | {definition['category']} |
| Trạng thái | `{manifest['use']}` |
| Phiên bản package | `{manifest['packageVersion']}` |
| Đích thực thi | `{manifest['executionTarget']}` |
| Inspector | `{manifest['inspector']['kind']}` |
| Khả năng | {capabilities} |

{runtime_notice(manifest['use'], vietnamese=True)}

## Port

| Key | Hướng | Kiểu dữ liệu | Bắt buộc | Variadic | Nhãn |
|---|---|---|---|---|---|
{port_rows([*inputs, *outputs], vietnamese=True)}

## Tham số

| Key | Kiểu | Mặc định | Nhỏ nhất | Lớn nhất | Lựa chọn | Ý nghĩa |
|---|---|---|---|---|---|---|
{parameter_rows(definition.get('parameters', []))}

## Cách dùng trong workflow

1. Thêm **{definition['name']}** từ nhóm **{definition['category']}** trong Workflow editor.
2. Nối input đúng kiểu: {input_keys}.
3. Cấu hình tham số trong giới hạn đã liệt kê.
4. Nối output: {output_keys}.
5. Lưu workflow trước khi bấm **Run** trong Project workspace.

Connection yêu cầu kiểu dữ liệu trùng tuyệt đối. Workflow vẫn là DAG; cycle và self-loop bị từ chối. `delay` và `bounded-repeat` cung cấp hành vi có giới hạn mà không tạo cycle trong graph.

## Bằng chứng và an toàn

Runtime lưu tham số, tóm tắt input/output, thời lượng, phiên bản, trạng thái và evidence hash. Mảng ảnh không được lưu trong JSON evidence. `image-output` đánh dấu ảnh mới nhất để mã hóa PNG và hiển thị trong 2D optical view.

- Trạng thái `{manifest['use']}` không đồng nghĩa được duyệt cho production.
- Phải kiểm tra kích thước, thứ tự channel, dtype, threshold, timing và memory trên phần cứng đích.
- Production mode từ chối mọi node chưa mang trạng thái `release`.
'''


def main() -> None:
    manifests = sorted(NODES_ROOT.glob('*/*/manifest.json'))
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest_path.with_name('README.md').write_text(render_english(manifest), encoding='utf-8')
        manifest_path.with_name('README.md.vn').write_text(render_vietnamese(manifest), encoding='utf-8')
    print(f'Generated bilingual documentation for {len(manifests)} node packages.')


if __name__ == '__main__':
    main()