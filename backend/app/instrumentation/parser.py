from __future__ import annotations

import ast
from dataclasses import dataclass

from app.instrumentation.injector import instrument_tree


@dataclass(slots=True)
class InstrumentationMetadata:
    line_numbers: list[int]
    function_names: list[str]
    loop_line_numbers: list[int]


@dataclass(slots=True)
class InstrumentedSource:
    original_source: str
    instrumented_source: str
    tree: ast.Module
    metadata: InstrumentationMetadata


def parse_source(source: str, filename: str = "<instrumented>") -> ast.Module:
    return ast.parse(source, filename=filename, mode="exec")


def collect_metadata(tree: ast.AST) -> InstrumentationMetadata:
    line_numbers = sorted({node.lineno for node in ast.walk(tree) if hasattr(node, "lineno")})
    function_names = sorted(
        {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    )
    loop_line_numbers = sorted(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, (ast.For, ast.AsyncFor, ast.While))
        }
    )
    return InstrumentationMetadata(
        line_numbers=line_numbers,
        function_names=function_names,
        loop_line_numbers=loop_line_numbers,
    )


def instrument_source(
    source: str,
    *,
    filename: str = "<instrumented>",
    tracker_name: str = "_big_o_tracker",
) -> InstrumentedSource:
    tree = parse_source(source, filename=filename)
    instrumented_tree = instrument_tree(tree, tracker_name=tracker_name)
    return InstrumentedSource(
        original_source=source,
        instrumented_source=ast.unparse(instrumented_tree),
        tree=instrumented_tree,
        metadata=collect_metadata(tree),
    )


def compile_instrumented_source(instrumented: InstrumentedSource, filename: str = "<instrumented>") -> code:
    return compile(instrumented.instrumented_source, filename, "exec")


__all__ = [
    "InstrumentationMetadata",
    "InstrumentedSource",
    "collect_metadata",
    "compile_instrumented_source",
    "instrument_source",
    "parse_source",
]
