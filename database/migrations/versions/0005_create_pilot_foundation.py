"""Create industrial pilot commissioning and integration foundation.

Revision ID: 0005_create_pilot_foundation
Revises: 0004_create_inspection_runtime
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0005_create_pilot_foundation'
down_revision = '0004_create_inspection_runtime'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'calibration_records',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('station_id', sa.String(128), nullable=False),
        sa.Column('camera_id', sa.String(128), nullable=False),
        sa.Column('calibration_type', sa.String(32), nullable=False),
        sa.Column('artifact_relative_path', sa.Text(), nullable=False),
        sa.Column('artifact_sha256', sa.String(64), nullable=False),
        sa.Column('metrics', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('valid','failed','expired','revoked')", name='ck_calibration_records_status'),
    )
    op.create_index('ix_calibration_records_station_id', 'calibration_records', ['station_id'])
    op.create_table(
        'commissioning_profiles',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('station_id', sa.String(128), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('deployment_mode', sa.String(32), nullable=False),
        sa.Column('calibration_id', sa.String(64), sa.ForeignKey('calibration_records.id', ondelete='RESTRICT')),
        sa.Column('signal_mapping', postgresql.JSONB(), nullable=False),
        sa.Column('integration_policy', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('station_id', 'version', name='uq_commissioning_profiles_station_version'),
        sa.CheckConstraint("deployment_mode IN ('simulation','hardware-pilot','production')", name='ck_commissioning_profiles_mode'),
    )
    op.create_index('ix_commissioning_profiles_station_id', 'commissioning_profiles', ['station_id'])
    op.create_index(
        'uq_commissioning_profiles_active_station', 'commissioning_profiles', ['station_id'],
        unique=True, postgresql_where=sa.text('is_active'),
    )
    op.create_table(
        'commissioning_activation_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('station_id', sa.String(128), nullable=False),
        sa.Column('profile_id', sa.String(64), sa.ForeignKey('commissioning_profiles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('previous_profile_id', sa.String(64), sa.ForeignKey('commissioning_profiles.id', ondelete='RESTRICT')),
        sa.Column('actor_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_commissioning_activation_events_station_id', 'commissioning_activation_events', ['station_id'])
    op.add_column('inspection_runs', sa.Column('station_id', sa.String(128), server_default='station-01', nullable=False))
    op.add_column('inspection_runs', sa.Column('work_order_id', sa.String(128), nullable=True))
    op.add_column('inspection_runs', sa.Column(
        'commissioning_snapshot', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False,
    ))
    op.create_table(
        'integration_outbox_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('idempotency_key', sa.String(200), unique=True, nullable=False),
        sa.Column('run_id', sa.String(64), sa.ForeignKey('inspection_runs.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('channel', sa.String(32), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(16), server_default='pending', nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_error', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("channel IN ('plc','mes','ipc-cfx','opc-ua')", name='ck_integration_outbox_channel'),
        sa.CheckConstraint("status IN ('pending','delivering','delivered','failed')", name='ck_integration_outbox_status'),
    )
    op.create_index('ix_integration_outbox_events_run_id', 'integration_outbox_events', ['run_id'])
    op.create_index('ix_integration_outbox_pending', 'integration_outbox_events', ['status', 'created_at'])


def downgrade() -> None:
    op.drop_table('integration_outbox_events')
    op.drop_column('inspection_runs', 'commissioning_snapshot')
    op.drop_column('inspection_runs', 'work_order_id')
    op.drop_column('inspection_runs', 'station_id')
    op.drop_table('commissioning_activation_events')
    op.drop_table('commissioning_profiles')
    op.drop_table('calibration_records')