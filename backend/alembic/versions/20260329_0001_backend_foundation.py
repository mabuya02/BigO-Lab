"""Initial backend foundation schema.

Revision ID: 20260329_0001
Revises:
Create Date: 2026-03-29 22:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"], unique=False)

    op.create_table(
        "code_snippets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("author_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False, server_default="python"),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_snippets_author_id", "code_snippets", ["author_id"], unique=False)
    op.create_index("ix_code_snippets_project_id", "code_snippets", ["project_id"], unique=False)

    op.create_table(
        "experiments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("snippet_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False, server_default="python"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("input_kind", sa.String(length=50), nullable=False, server_default="array"),
        sa.Column("input_profile", sa.String(length=80), nullable=True),
        sa.Column("input_sizes", sa.JSON(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snippet_id"], ["code_snippets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiments_created_by_id", "experiments", ["created_by_id"], unique=False)
    op.create_index("ix_experiments_project_id", "experiments", ["project_id"], unique=False)
    op.create_index("ix_experiments_snippet_id", "experiments", ["snippet_id"], unique=False)

    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("experiment_id", sa.String(length=36), nullable=False),
        sa.Column("input_size", sa.Integer(), nullable=False),
        sa.Column("repetition_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_profile", sa.String(length=80), nullable=True),
        sa.Column("input_payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("backend", sa.String(length=50), nullable=True),
        sa.Column("runtime_ms", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("timed_out", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("truncated_stdout", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("truncated_stderr", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_runs_experiment_id", "experiment_runs", ["experiment_id"], unique=False)
    op.create_index("ix_experiment_runs_input_size", "experiment_runs", ["input_size"], unique=False)

    op.create_table(
        "line_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("experiment_run_id", sa.String(length=36), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("execution_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("percentage_of_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("nesting_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loop_iterations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("branch_visits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_run_id"], ["experiment_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_line_metrics_experiment_run_id", "line_metrics", ["experiment_run_id"], unique=False)
    op.create_index("ix_line_metrics_line_number", "line_metrics", ["line_number"], unique=False)

    op.create_table(
        "function_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("experiment_run_id", sa.String(length=36), nullable=False),
        sa.Column("function_name", sa.String(length=160), nullable=False),
        sa.Column("qualified_name", sa.String(length=255), nullable=True),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("self_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_recursive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_run_id"], ["experiment_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_function_metrics_experiment_run_id", "function_metrics", ["experiment_run_id"], unique=False)
    op.create_index("ix_function_metrics_function_name", "function_metrics", ["function_name"], unique=False)

    op.create_table(
        "complexity_estimates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("experiment_id", sa.String(length=36), nullable=True),
        sa.Column("metric_name", sa.String(length=80), nullable=False),
        sa.Column("estimated_class", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("alternatives", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_complexity_estimates_experiment_id", "complexity_estimates", ["experiment_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_complexity_estimates_experiment_id", table_name="complexity_estimates")
    op.drop_table("complexity_estimates")

    op.drop_index("ix_function_metrics_function_name", table_name="function_metrics")
    op.drop_index("ix_function_metrics_experiment_run_id", table_name="function_metrics")
    op.drop_table("function_metrics")

    op.drop_index("ix_line_metrics_line_number", table_name="line_metrics")
    op.drop_index("ix_line_metrics_experiment_run_id", table_name="line_metrics")
    op.drop_table("line_metrics")

    op.drop_index("ix_experiment_runs_input_size", table_name="experiment_runs")
    op.drop_index("ix_experiment_runs_experiment_id", table_name="experiment_runs")
    op.drop_table("experiment_runs")

    op.drop_index("ix_experiments_snippet_id", table_name="experiments")
    op.drop_index("ix_experiments_project_id", table_name="experiments")
    op.drop_index("ix_experiments_created_by_id", table_name="experiments")
    op.drop_table("experiments")

    op.drop_index("ix_code_snippets_project_id", table_name="code_snippets")
    op.drop_index("ix_code_snippets_author_id", table_name="code_snippets")
    op.drop_table("code_snippets")

    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
