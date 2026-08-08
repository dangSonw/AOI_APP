from core.algorithms import DataType, ParameterKind, get_algorithm_catalog, get_algorithm_definition


def test_catalog_contains_every_approved_configuration_definition() -> None:
    catalog = get_algorithm_catalog()

    assert len(catalog) == 58
    assert len({item.id for item in catalog}) == len(catalog)
    assert all(item.availability == 'configuration-only' for item in catalog)
    assert all(item.name and item.description and item.category for item in catalog)


def test_catalog_port_keys_are_unique_per_definition_and_fully_typed() -> None:
    for definition in get_algorithm_catalog():
        keys = [port.key for port in (*definition.inputs, *definition.outputs)]

        assert len(keys) == len(set(keys)), definition.id
        assert all(port.label for port in (*definition.inputs, *definition.outputs))
        assert all(isinstance(port.data_type, DataType) for port in (*definition.inputs, *definition.outputs))


def test_catalog_parameters_have_defaults_and_constraints() -> None:
    for definition in get_algorithm_catalog():
        keys = [parameter.key for parameter in definition.parameters]
        assert len(keys) == len(set(keys)), definition.id
        for parameter in definition.parameters:
            assert isinstance(parameter.kind, ParameterKind)
            if parameter.kind is ParameterKind.SELECT:
                assert parameter.options
                assert parameter.default_value in parameter.options
            if parameter.kind in (ParameterKind.INTEGER, ParameterKind.NUMBER):
                if parameter.minimum is not None:
                    assert parameter.default_value >= parameter.minimum
                if parameter.maximum is not None:
                    assert parameter.default_value <= parameter.maximum


def test_decision_fusion_accepts_variadic_scores() -> None:
    definition = get_algorithm_definition('decision-fusion')

    assert definition is not None
    assert definition.inputs[0].data_type is DataType.SCORE
    assert definition.inputs[0].variadic is True
    assert definition.inputs[0].required is True


def test_documented_reference_algorithms_can_be_looked_up() -> None:
    assert get_algorithm_definition('median-mad-robust-difference').name == 'Median–MAD robust difference'
    assert get_algorithm_definition('patchcore').documentation_group == 'Group B — Feature distribution'
    assert get_algorithm_definition('does-not-exist') is None

def test_parameter_values_support_bounded_json_compatible_structures() -> None:
    from core.algorithms import is_json_parameter_value

    assert is_json_parameter_value({'roi': [1, 2, 3], 'enabled': True, 'model': None})
    assert not is_json_parameter_value({'depth': [[[[[[[[[[1]]]]]]]]]]}, maximum_depth=4)
    assert not is_json_parameter_value({'unsafe': object()})
