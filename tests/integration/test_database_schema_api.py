from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, MetaData, String, Table, UniqueConstraint, create_engine

from app.auth.dependencies import get_current_user
from app.main import app
from app.services.database_schema_service import inspect_database_schema


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, is_active=True)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_database_schema_requires_authentication() -> None:
    with TestClient(app) as anonymous_client:
        assert anonymous_client.get('/api/database/schema').status_code == 401


def test_database_schema_returns_normalized_metadata(client: TestClient) -> None:
    response = client.get('/api/database/schema')

    assert response.status_code == 200
    payload = response.json()
    assert payload['databaseDialect'] in {'postgresql', 'sqlite'}
    assert all({'schema', 'name', 'columns', 'indexes', 'constraints', 'foreignKeys'} <= table.keys()
               for table in payload['tables'])
    assert all({'name', 'sourceColumns', 'targetSchema', 'targetTable', 'targetColumns'} <= foreign_key.keys()
               for table in payload['tables'] for foreign_key in table['foreignKeys'])


def test_schema_inspector_preserves_keys_indexes_and_constraints() -> None:
    engine = create_engine('sqlite://')
    metadata = MetaData()
    Table('parents', metadata, Column('id', Integer, primary_key=True))
    children = Table(
        'children', metadata,
        Column('id', Integer, primary_key=True),
        Column('parent_id', ForeignKey('parents.id', ondelete='CASCADE'), nullable=False),
        Column('code', String(20), nullable=False),
        UniqueConstraint('code', name='uq_children_code'),
        CheckConstraint("code <> ''", name='ck_children_code'),
    )
    Index('ix_children_parent_id', children.c.parent_id)
    metadata.create_all(engine)

    payload = inspect_database_schema(engine).model_dump(mode='json', by_alias=True)
    table = next(item for item in payload['tables'] if item['name'] == 'children')

    assert next(column for column in table['columns'] if column['name'] == 'id')['primaryKey'] is True
    assert table['indexes'][0]['columnNames'] == ['parent_id']
    assert table['constraints']['primaryKey']['columnNames'] == ['id']
    assert table['constraints']['unique'][0]['columnNames'] == ['code']
    assert table['constraints']['check'][0]['expression'] == "code <> ''"
    assert table['foreignKeys'][0]['targetTable'] == 'parents'
    assert table['foreignKeys'][0]['onDelete'] == 'CASCADE'