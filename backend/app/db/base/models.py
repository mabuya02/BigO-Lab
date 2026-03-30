from __future__ import annotations


def import_all_models() -> None:
    # Import models lazily so Base can be imported without creating circular references.
    from app.models.code_snippet import CodeSnippet  # noqa: F401
    from app.models.complexity_estimate import ComplexityEstimate  # noqa: F401
    from app.models.experiment import Experiment  # noqa: F401
    from app.models.experiment_run import ExperimentRun  # noqa: F401
    from app.models.function_metric import FunctionMetric  # noqa: F401
    from app.models.line_metric import LineMetric  # noqa: F401
    from app.models.project import Project  # noqa: F401
    from app.models.user import User  # noqa: F401
