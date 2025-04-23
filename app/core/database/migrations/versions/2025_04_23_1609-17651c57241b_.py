"""empty message

Revision ID: 17651c57241b
Revises: 6d7c9baf7b92
Create Date: 2025-04-23 16:09:59.934549

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "17651c57241b"
down_revision: str | None = "ea84e7a02b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.drop_constraint("pk_question_to_theme", "question_to_theme", type_="primary")
    op.create_primary_key(
        "pk_question_to_theme", "question_to_theme", ["round_id", "theme_id", "question_id"]
    )


def downgrade():
    op.drop_constraint("pk_question_to_theme", "question_to_theme", type_="primary")
    op.create_primary_key(
        "pk_question_to_theme", "question_to_theme", ["theme_id", "question_id"]
    )
