"""Create existing AOI schema baseline."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0001_existing_schema_baseline'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('email', sa.String(320), nullable=False),
        sa.Column('full_name', sa.String(120), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'recipes',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('slug', sa.String(128), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_recipes_slug', 'recipes', ['slug'])
    op.create_index('ix_recipes_is_active', 'recipes', ['is_active'])

    op.create_table(
        'inspection_results',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('board_serial', sa.String(128), nullable=False),
        sa.Column('lot', sa.String(128), server_default='', nullable=False),
        sa.Column('recipe_id', sa.BigInteger(), sa.ForeignKey('recipes.id'), nullable=False),
        sa.Column('recipe_name', sa.String(255), nullable=False),
        sa.Column('operator_id', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('result', sa.String(10), nullable=False),
        sa.Column('defect_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('score', sa.REAL(), nullable=True),
        sa.Column('cycle_time_ms', sa.Integer(), nullable=True),
        sa.Column('camera_config', postgresql.JSONB(), nullable=True),
        sa.Column('review_decision', sa.String(10), nullable=True),
        sa.Column('reviewed_by', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('inspected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("result IN ('PASS', 'FAIL', 'REVIEW')", name='ck_inspection_results_result'),
        sa.CheckConstraint("review_decision IS NULL OR review_decision IN ('PASS', 'FAIL')", name='ck_inspection_results_review_decision'),
    )
    for column in ('board_serial', 'lot', 'result', 'recipe_id', 'operator_id'):
        op.create_index(f'ix_inspection_results_{column}', 'inspection_results', [column])
    op.create_index('ix_inspection_results_inspected_at', 'inspection_results', [sa.text('inspected_at DESC')])

    op.create_table(
        'defects',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('result_id', sa.BigInteger(), sa.ForeignKey('inspection_results.id', ondelete='CASCADE'), nullable=False),
        sa.Column('defect_type', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(20), server_default='medium', nullable=False),
        sa.Column('location_x', sa.REAL(), nullable=True),
        sa.Column('location_y', sa.REAL(), nullable=True),
        sa.Column('width', sa.REAL(), nullable=True),
        sa.Column('height', sa.REAL(), nullable=True),
        sa.Column('confidence', sa.REAL(), nullable=True),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='ck_defects_severity'),
    )
    for column in ('result_id', 'defect_type', 'severity'):
        op.create_index(f'ix_defects_{column}', 'defects', [column])

    op.create_table(
        'inspection_images',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('result_id', sa.BigInteger(), sa.ForeignKey('inspection_results.id', ondelete='CASCADE'), nullable=False),
        sa.Column('defect_id', sa.BigInteger(), sa.ForeignKey('defects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('image_type', sa.String(32), nullable=False),
        sa.Column('relative_path', sa.String(512), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('width_px', sa.Integer(), nullable=True),
        sa.Column('height_px', sa.Integer(), nullable=True),
        sa.Column('sha256_hash', sa.String(64), nullable=True),
        sa.Column('media_type', sa.String(64), server_default='image/png', nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("image_type IN ('original', 'annotated', 'evidence', 'thumbnail')", name='ck_inspection_images_image_type'),
    )
    for column in ('result_id', 'defect_id', 'image_type'):
        op.create_index(f'ix_inspection_images_{column}', 'inspection_images', [column])

    op.create_table(
        'audit_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('actor_id', sa.BigInteger(), nullable=True),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('method', sa.String(8), nullable=False),
        sa.Column('path', sa.String(512), nullable=False),
        sa.Column('resource_type', sa.String(128), nullable=False),
        sa.Column('resource_id', sa.String(256), nullable=True),
        sa.Column('request_id', sa.String(128), nullable=False, unique=True),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('result', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ('actor_id', 'action', 'path', 'resource_type', 'result', 'created_at'):
        op.create_index(f'ix_audit_events_{column}', 'audit_events', [column])


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('inspection_images')
    op.drop_table('defects')
    op.drop_table('inspection_results')
    op.drop_table('recipes')
    op.drop_table('users')