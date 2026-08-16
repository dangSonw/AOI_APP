from typing import Any

from sqlalchemy import inspect
from sqlalchemy.engine import Connection, Engine

from app.schemas.database_schema import (
    DatabaseCheckConstraintSchema,
    DatabaseColumnSchema,
    DatabaseForeignKeySchema,
    DatabaseIndexSchema,
    DatabaseNamedColumnsSchema,
    DatabaseSchemaResponse,
    DatabaseTableConstraintsSchema,
    DatabaseTableSchema,
)


def _column_names(value: dict[str, Any]) -> list[str]:
    names = value.get('column_names', value.get('constrained_columns', []))
    return [name for name in names if isinstance(name, str)]


def inspect_database_schema(bind: Engine | Connection) -> DatabaseSchemaResponse:
    inspector = inspect(bind)
    schema_name = inspector.default_schema_name or 'public'
    tables: list[DatabaseTableSchema] = []

    for table_name in sorted(inspector.get_table_names(schema=schema_name)):
        primary_key = inspector.get_pk_constraint(table_name, schema=schema_name)
        primary_key_columns = set(_column_names(primary_key))
        unique_constraints = inspector.get_unique_constraints(table_name, schema=schema_name)
        try:
            check_constraints = inspector.get_check_constraints(table_name, schema=schema_name)
        except NotImplementedError:
            check_constraints = []

        tables.append(DatabaseTableSchema(
            schema_name=schema_name,
            name=table_name,
            columns=[DatabaseColumnSchema(
                name=column['name'],
                data_type=str(column['type']),
                nullable=bool(column.get('nullable', True)),
                default=None if column.get('default') is None else str(column['default']),
                primary_key=column['name'] in primary_key_columns,
            ) for column in inspector.get_columns(table_name, schema=schema_name)],
            indexes=[DatabaseIndexSchema(
                name=index.get('name'),
                column_names=_column_names(index),
                unique=bool(index.get('unique', False)),
            ) for index in inspector.get_indexes(table_name, schema=schema_name)],
            constraints=DatabaseTableConstraintsSchema(
                primary_key=DatabaseNamedColumnsSchema(
                    name=primary_key.get('name'),
                    column_names=_column_names(primary_key),
                ) if primary_key_columns else None,
                unique=[DatabaseNamedColumnsSchema(
                    name=constraint.get('name'),
                    column_names=_column_names(constraint),
                ) for constraint in unique_constraints],
                check=[DatabaseCheckConstraintSchema(
                    name=constraint.get('name'),
                    expression=str(constraint.get('sqltext', '')),
                ) for constraint in check_constraints],
            ),
            foreign_keys=[DatabaseForeignKeySchema(
                name=foreign_key.get('name'),
                source_columns=_column_names({'column_names': foreign_key.get('constrained_columns', [])}),
                target_schema=foreign_key.get('referred_schema') or schema_name,
                target_table=foreign_key['referred_table'],
                target_columns=_column_names({'column_names': foreign_key.get('referred_columns', [])}),
                on_update=foreign_key.get('options', {}).get('onupdate'),
                on_delete=foreign_key.get('options', {}).get('ondelete'),
            ) for foreign_key in inspector.get_foreign_keys(table_name, schema=schema_name)],
        ))

    return DatabaseSchemaResponse(
        database_dialect=bind.dialect.name,
        default_schema=schema_name,
        tables=tables,
    )