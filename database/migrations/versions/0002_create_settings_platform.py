"""Create versioned settings platform."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0002_create_settings_platform'
down_revision: str | None = '0001_existing_schema_baseline'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'settings_documents',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('scope', sa.String(32), nullable=False),
        sa.Column('subject_id', sa.String(256), nullable=False),
        sa.Column('document_key', sa.String(128), nullable=False),
        sa.Column('owner_user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('current_revision', sa.Integer(), server_default='0', nullable=False),
        sa.Column('current_version_id', sa.BigInteger(), nullable=True),
        sa.Column('active_version_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("scope IN ('user', 'workstation', 'recipe', 'system')", name='ck_settings_documents_scope'),
        sa.CheckConstraint('current_revision >= 0', name='ck_settings_documents_current_revision'),
    )
    op.execute(
        'ALTER TABLE settings_documents ADD CONSTRAINT uq_settings_documents_identity '
        'UNIQUE NULLS NOT DISTINCT (scope, subject_id, document_key, owner_user_id)'
    )
    op.create_index('ix_settings_documents_identity', 'settings_documents', ['scope', 'subject_id', 'document_key'])

    op.create_table(
        'settings_versions',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('document_id', sa.BigInteger(), sa.ForeignKey('settings_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('schema_version', sa.Integer(), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('created_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('reason', sa.Text(), server_default='', nullable=False),
        sa.Column('source_version_id', sa.BigInteger(), sa.ForeignKey('settings_versions.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('revision >= 1', name='ck_settings_versions_revision'),
        sa.CheckConstraint('schema_version >= 1', name='ck_settings_versions_schema_version'),
        sa.UniqueConstraint('document_id', 'revision', name='uq_settings_versions_document_revision'),
    )
    op.create_index('ix_settings_versions_history', 'settings_versions', ['document_id', 'revision'])
    op.create_foreign_key(
        'fk_settings_documents_current_version', 'settings_documents', 'settings_versions',
        ['current_version_id'], ['id'], ondelete='RESTRICT',
    )
    op.create_foreign_key(
        'fk_settings_documents_active_version', 'settings_documents', 'settings_versions',
        ['active_version_id'], ['id'], ondelete='RESTRICT',
    )

    op.create_table(
        'settings_activations',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('document_id', sa.BigInteger(), sa.ForeignKey('settings_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requested_version_id', sa.BigInteger(), sa.ForeignKey('settings_versions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('idempotency_key', sa.String(128), nullable=False),
        sa.Column('request_checksum', sa.String(64), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('observed_target_revision', sa.String(128), nullable=True),
        sa.Column('diagnostics', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('requested_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('reason', sa.Text(), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'failed')", name='ck_settings_activations_status'),
        sa.UniqueConstraint('document_id', 'idempotency_key', name='uq_settings_activations_document_key'),
    )
    op.create_index('ix_settings_activations_history', 'settings_activations', ['document_id', 'created_at'])

    op.add_column('audit_events', sa.Column('before_checksum', sa.String(64), nullable=True))
    op.add_column('audit_events', sa.Column('after_checksum', sa.String(64), nullable=True))
    op.add_column('audit_events', sa.Column('reason', sa.Text(), nullable=True))
    op.add_column('audit_events', sa.Column('client_metadata', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('audit_events', 'client_metadata')
    op.drop_column('audit_events', 'reason')
    op.drop_column('audit_events', 'after_checksum')
    op.drop_column('audit_events', 'before_checksum')
    op.drop_table('settings_activations')
    op.drop_constraint('fk_settings_documents_active_version', 'settings_documents', type_='foreignkey')
    op.drop_constraint('fk_settings_documents_current_version', 'settings_documents', type_='foreignkey')
    op.drop_table('settings_versions')
    op.drop_table('settings_documents')