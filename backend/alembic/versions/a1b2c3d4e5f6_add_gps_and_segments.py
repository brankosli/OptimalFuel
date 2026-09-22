"""add gps columns to activities and segment_efforts table

Revision ID: a1b2c3d4e5f6
Revises: d7ad46cf93e8
Create Date: 2026-04-18 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd7ad46cf93e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add GPS + sync columns to activities
    with op.batch_alter_table('activities') as batch_op:
        batch_op.add_column(sa.Column('start_lat', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('start_lng', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('end_lat', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('end_lng', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('summary_polyline', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('segments_synced', sa.Boolean(), nullable=False, server_default='0'))

    # Create segment_efforts table
    op.create_table(
        'segment_efforts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('activity_id', sa.Integer(), nullable=False, index=True),
        sa.Column('strava_segment_id', sa.Integer(), nullable=False, index=True),
        sa.Column('strava_effort_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('effort_date', sa.Date(), nullable=False, index=True),
        sa.Column('elapsed_time', sa.Integer(), nullable=False),
        sa.Column('moving_time', sa.Integer(), nullable=True),
        sa.Column('distance_meters', sa.Float(), nullable=True),
        sa.Column('avg_heart_rate', sa.Float(), nullable=True),
        sa.Column('avg_watts', sa.Float(), nullable=True),
        sa.Column('avg_cadence', sa.Float(), nullable=True),
        sa.Column('pr_rank', sa.Integer(), nullable=True),
        sa.Column('kom_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('segment_efforts')
    with op.batch_alter_table('activities') as batch_op:
        batch_op.drop_column('segments_synced')
        batch_op.drop_column('summary_polyline')
        batch_op.drop_column('end_lng')
        batch_op.drop_column('end_lat')
        batch_op.drop_column('start_lng')
        batch_op.drop_column('start_lat')
