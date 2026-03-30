from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Import models so Alembic and metadata discovery can see every mapped table.
from app.models.code_snippet import CodeSnippet  # noqa: E402,F401
from app.models.complexity_estimate import ComplexityEstimate  # noqa: E402,F401
from app.models.experiment import Experiment  # noqa: E402,F401
from app.models.experiment_run import ExperimentRun  # noqa: E402,F401
from app.models.function_metric import FunctionMetric  # noqa: E402,F401
from app.models.line_metric import LineMetric  # noqa: E402,F401
from app.models.project import Project  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
