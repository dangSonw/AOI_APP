from pydantic import Field

from app.schemas.base import ApiSchema


class DatabaseColumnSchema(ApiSchema):
    name: str
    data_type: str
    nullable: bool
    default: str | None = None
    primary_key: bool = False


class DatabaseIndexSchema(ApiSchema):
    name: str | None = None
    column_names: list[str]
    unique: bool = False


class DatabaseNamedColumnsSchema(ApiSchema):
    name: str | None = None
    column_names: list[str]


class DatabaseCheckConstraintSchema(ApiSchema):
    name: str | None = None
    expression: str


class DatabaseTableConstraintsSchema(ApiSchema):
    primary_key: DatabaseNamedColumnsSchema | None = None
    unique: list[DatabaseNamedColumnsSchema]
    check: list[DatabaseCheckConstraintSchema]


class DatabaseForeignKeySchema(ApiSchema):
    name: str | None = None
    source_columns: list[str]
    target_schema: str
    target_table: str
    target_columns: list[str]
    on_update: str | None = None
    on_delete: str | None = None


class DatabaseTableSchema(ApiSchema):
    schema_name: str = Field(serialization_alias='schema')
    name: str
    columns: list[DatabaseColumnSchema]
    indexes: list[DatabaseIndexSchema]
    constraints: DatabaseTableConstraintsSchema
    foreign_keys: list[DatabaseForeignKeySchema]


class DatabaseSchemaResponse(ApiSchema):
    database_dialect: str
    default_schema: str
    tables: list[DatabaseTableSchema]