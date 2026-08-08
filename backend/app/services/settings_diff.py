import hashlib
import json
from collections.abc import Mapping
from typing import Any


def canonical_settings_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def settings_checksum(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_settings_json(payload).encode('utf-8')).hexdigest()


def settings_diff(submitted: Any, current: Any, path: str = '$') -> list[dict[str, Any]]:
    if isinstance(submitted, dict) and isinstance(current, dict):
        differences: list[dict[str, Any]] = []
        for key in sorted(set(submitted) | set(current)):
            child_path = f'{path}.{key}'
            if key not in submitted:
                differences.append({'path': child_path, 'submitted': None, 'current': current[key]})
            elif key not in current:
                differences.append({'path': child_path, 'submitted': submitted[key], 'current': None})
            else:
                differences.extend(settings_diff(submitted[key], current[key], child_path))
        return differences
    if isinstance(submitted, list) and isinstance(current, list):
        differences = []
        for index in range(max(len(submitted), len(current))):
            child_path = f'{path}[{index}]'
            if index >= len(submitted):
                differences.append({'path': child_path, 'submitted': None, 'current': current[index]})
            elif index >= len(current):
                differences.append({'path': child_path, 'submitted': submitted[index], 'current': None})
            else:
                differences.extend(settings_diff(submitted[index], current[index], child_path))
        return differences
    if submitted != current:
        return [{'path': path, 'submitted': submitted, 'current': current}]
    return []