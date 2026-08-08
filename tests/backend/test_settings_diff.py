def test_checksum_ignores_mapping_order() -> None:
    from app.services.settings_diff import settings_checksum

    assert settings_checksum({'b': 2, 'a': 1}) == settings_checksum({'a': 1, 'b': 2})


def test_diff_uses_sorted_json_paths() -> None:
    from app.services.settings_diff import settings_diff

    assert settings_diff({'z': 1, 'nested': {'value': 3}}, {'z': 2, 'nested': {'value': 4}}) == [
        {'path': '$.nested.value', 'submitted': 3, 'current': 4},
        {'path': '$.z', 'submitted': 1, 'current': 2},
    ]