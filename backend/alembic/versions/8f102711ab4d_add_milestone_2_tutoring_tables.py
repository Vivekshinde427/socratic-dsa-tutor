"""add_milestone_2_tutoring_tables

Revision ID: 8f102711ab4d
Revises: 791644889ceb
Create Date: 2026-10-09 00:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '8f102711ab4d'
down_revision: Union[str, Sequence[str], None] = '791644889ceb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. sessions
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', sa.String(), sa.ForeignKey('problems.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', sa.String(), sa.ForeignKey('problem_plans.id', ondelete='SET NULL'), nullable=True),
        sa.Column('current_step_index', sa.Integer(), nullable=False, default=0),
        sa.Column('current_hint_level', sa.Integer(), nullable=False, default=0),
        sa.Column('current_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.String(), nullable=False, default='active'),
        sa.Column('stage_progress', sa.JSON(), nullable=False),
        sa.Column('rolling_summary', sa.Text(), nullable=False, default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_sessions_problem_id'), 'sessions', ['problem_id'], unique=False)

    # 2. messages
    op.create_table(
        'messages',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('session_id', sa.String(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(), nullable=False, default='text'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_messages_session_id'), 'messages', ['session_id'], unique=False)

    # 3. feedback
    op.create_table(
        'feedback',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('session_id', sa.String(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=False, default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_feedback_session_id'), 'feedback', ['session_id'], unique=False)

    # 4. learning_progress
    op.create_table(
        'learning_progress',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('mastery', sa.Float(), nullable=False, default=0.0),
        sa.Column('problems_attempted', sa.Integer(), nullable=False, default=0),
        sa.Column('problems_completed', sa.Integer(), nullable=False, default=0),
        sa.Column('total_hints_used', sa.Integer(), nullable=False, default=0),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_learning_progress_user_id'), 'learning_progress', ['user_id'], unique=False)
    op.create_index(op.f('ix_learning_progress_topic'), 'learning_progress', ['topic'], unique=False)

    # 5. mcq_attempts
    op.create_table(
        'mcq_attempts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('session_id', sa.String(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_id', sa.String(), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False, default=0),
        sa.Column('selected_option_id', sa.String(), nullable=False),
        sa.Column('correct', sa.Boolean(), nullable=False),
        sa.Column('misconception_id', sa.String(), nullable=True),
        sa.Column('hint_level_at_attempt', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_mcq_attempts_session_id'), 'mcq_attempts', ['session_id'], unique=False)

    # 6. code_runs
    op.create_table(
        'code_runs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('session_id', sa.String(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('language', sa.String(), nullable=False, default='python'),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('run_type', sa.String(), nullable=False, default='run'),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('stdout', sa.Text(), nullable=False, default=''),
        sa.Column('stderr', sa.Text(), nullable=False, default=''),
        sa.Column('execution_time_ms', sa.Float(), nullable=False, default=0.0),
        sa.Column('tests_passed', sa.Integer(), nullable=True),
        sa.Column('tests_total', sa.Integer(), nullable=True),
        sa.Column('test_results', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_code_runs_session_id'), 'code_runs', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_table('code_runs')
    op.drop_table('mcq_attempts')
    op.drop_table('learning_progress')
    op.drop_table('feedback')
    op.drop_table('messages')
    op.drop_table('sessions')
