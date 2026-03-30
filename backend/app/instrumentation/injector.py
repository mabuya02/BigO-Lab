from __future__ import annotations

import ast
from dataclasses import dataclass


def _is_docstring_statement(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_future_import(node: ast.stmt) -> bool:
    return isinstance(node, ast.ImportFrom) and node.module == "__future__"


def _tracker_call(tracker_name: str, method_name: str, *args: ast.expr) -> ast.Expr:
    return ast.Expr(
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=tracker_name, ctx=ast.Load()),
                attr=method_name,
                ctx=ast.Load(),
            ),
            args=list(args),
            keywords=[],
        )
    )


@dataclass(slots=True)
class InstrumentationContext:
    tracker_name: str = "_big_o_tracker"
    scope_stack: tuple[str, ...] = ()

    @property
    def qualname(self) -> str:
        return ".".join(self.scope_stack) if self.scope_stack else "<module>"

    def child(self, name: str) -> "InstrumentationContext":
        return InstrumentationContext(
            tracker_name=self.tracker_name,
            scope_stack=self.scope_stack + (name,),
        )


class InstrumentationInjector:
    def __init__(self, tracker_name: str = "_big_o_tracker") -> None:
        self.tracker_name = tracker_name

    def instrument(self, tree: ast.AST) -> ast.AST:
        if not isinstance(tree, ast.Module):
            raise TypeError("instrument() expects an ast.Module")
        new_tree = self._instrument_module(tree)
        ast.fix_missing_locations(new_tree)
        return new_tree

    def _instrument_module(self, node: ast.Module) -> ast.Module:
        prologue, rest = self._split_module_prologue(node.body)
        new_body = list(prologue)
        new_body.extend(self._instrument_statement_list(rest, InstrumentationContext(self.tracker_name)))
        node.body = new_body
        return node

    def _instrument_statement_list(
        self,
        body: list[ast.stmt],
        context: InstrumentationContext,
        *,
        preserve_docstring: bool = False,
    ) -> list[ast.stmt]:
        if not body:
            return []

        prologue, rest = self._split_body_prologue(body, preserve_docstring=preserve_docstring)
        instrumented: list[ast.stmt] = list(prologue)
        for stmt in rest:
            transformed = self._instrument_statement(stmt, context)
            probe = _tracker_call(
                context.tracker_name,
                "line",
                ast.Constant(value=getattr(stmt, "lineno", 0)),
            )
            ast.copy_location(probe, stmt)
            instrumented.append(probe)
            if isinstance(transformed, list):
                instrumented.extend(transformed)
            else:
                instrumented.append(transformed)
        return instrumented

    def _instrument_statement(
        self,
        stmt: ast.stmt,
        context: InstrumentationContext,
    ) -> ast.stmt | list[ast.stmt]:
        if isinstance(stmt, ast.FunctionDef):
            return self._instrument_function(stmt, context)
        if isinstance(stmt, ast.AsyncFunctionDef):
            return self._instrument_async_function(stmt, context)
        if isinstance(stmt, ast.ClassDef):
            return self._instrument_class(stmt, context)
        if isinstance(stmt, ast.For):
            return self._instrument_for(stmt, context)
        if isinstance(stmt, ast.AsyncFor):
            return self._instrument_async_for(stmt, context)
        if isinstance(stmt, ast.While):
            return self._instrument_while(stmt, context)
        if isinstance(stmt, ast.If):
            return self._instrument_if(stmt, context)
        if isinstance(stmt, ast.With):
            return self._instrument_with(stmt, context)
        if isinstance(stmt, ast.AsyncWith):
            return self._instrument_async_with(stmt, context)
        if isinstance(stmt, ast.Try):
            return self._instrument_try(stmt, context)
        if hasattr(ast, "Match") and isinstance(stmt, ast.Match):  # pragma: no cover - py311+
            return self._instrument_match(stmt, context)
        return self._transform_simple_statement(stmt)

    def _instrument_function(self, node: ast.FunctionDef, context: InstrumentationContext) -> ast.FunctionDef:
        child_context = context.child(node.name)
        node.body = self._instrument_statement_list(node.body, child_context, preserve_docstring=True)
        function_probe = _tracker_call(
            context.tracker_name,
            "function_call",
            ast.Constant(value=child_context.qualname),
        )
        ast.copy_location(function_probe, node)
        node.body.insert(self._body_insert_index(node.body, preserve_docstring=True), function_probe)
        return node

    def _instrument_async_function(
        self,
        node: ast.AsyncFunctionDef,
        context: InstrumentationContext,
    ) -> ast.AsyncFunctionDef:
        child_context = context.child(node.name)
        node.body = self._instrument_statement_list(node.body, child_context, preserve_docstring=True)
        function_probe = _tracker_call(
            context.tracker_name,
            "function_call",
            ast.Constant(value=child_context.qualname),
        )
        ast.copy_location(function_probe, node)
        node.body.insert(self._body_insert_index(node.body, preserve_docstring=True), function_probe)
        return node

    def _instrument_class(self, node: ast.ClassDef, context: InstrumentationContext) -> ast.ClassDef:
        child_context = context.child(node.name)
        node.body = self._instrument_statement_list(node.body, child_context, preserve_docstring=True)
        return node

    def _instrument_for(self, node: ast.For, context: InstrumentationContext) -> ast.For:
        node.target = self._visit_expr(node.target)
        node.iter = self._visit_expr(node.iter)
        node.body = self._instrument_loop_body(
            node.body,
            context,
            node.lineno,
            "For",
        )
        node.orelse = self._instrument_statement_list(node.orelse, context)
        return node

    def _instrument_async_for(self, node: ast.AsyncFor, context: InstrumentationContext) -> ast.AsyncFor:
        node.target = self._visit_expr(node.target)
        node.iter = self._visit_expr(node.iter)
        node.body = self._instrument_loop_body(
            node.body,
            context,
            node.lineno,
            "AsyncFor",
        )
        node.orelse = self._instrument_statement_list(node.orelse, context)
        return node

    def _instrument_while(self, node: ast.While, context: InstrumentationContext) -> ast.While:
        node.test = self._visit_expr(node.test)
        node.body = self._instrument_loop_body(
            node.body,
            context,
            node.lineno,
            "While",
        )
        node.orelse = self._instrument_statement_list(node.orelse, context)
        return node

    def _instrument_if(self, node: ast.If, context: InstrumentationContext) -> ast.If:
        node.test = self._visit_expr(node.test)
        node.body = self._instrument_statement_list(node.body, context)
        node.orelse = self._instrument_statement_list(node.orelse, context)
        return node

    def _instrument_with(self, node: ast.With, context: InstrumentationContext) -> ast.With:
        node.items = [self._visit_with_item(item) for item in node.items]
        node.body = self._instrument_statement_list(node.body, context)
        return node

    def _instrument_async_with(self, node: ast.AsyncWith, context: InstrumentationContext) -> ast.AsyncWith:
        node.items = [self._visit_with_item(item) for item in node.items]
        node.body = self._instrument_statement_list(node.body, context)
        return node

    def _instrument_try(self, node: ast.Try, context: InstrumentationContext) -> ast.Try:
        node.body = self._instrument_statement_list(node.body, context)
        node.handlers = [self._instrument_except_handler(handler, context) for handler in node.handlers]
        node.orelse = self._instrument_statement_list(node.orelse, context)
        node.finalbody = self._instrument_statement_list(node.finalbody, context)
        return node

    def _instrument_except_handler(self, node: ast.ExceptHandler, context: InstrumentationContext) -> ast.ExceptHandler:
        if node.type is not None:
            node.type = self._visit_expr(node.type)
        node.body = self._instrument_statement_list(node.body, context)
        return node

    def _instrument_match(self, node: ast.Match, context: InstrumentationContext) -> ast.Match:
        node.subject = self._visit_expr(node.subject)
        node.cases = [self._instrument_match_case(case, context) for case in node.cases]
        return node

    def _instrument_match_case(self, node, context: InstrumentationContext):  # type: ignore[no-untyped-def]
        if hasattr(node, "pattern"):
            node.pattern = self._visit_expr(node.pattern) if isinstance(node.pattern, ast.AST) else node.pattern
        if getattr(node, "guard", None) is not None:
            node.guard = self._visit_expr(node.guard)
        node.body = self._instrument_statement_list(node.body, context)
        return node

    def _instrument_loop_body(
        self,
        body: list[ast.stmt],
        context: InstrumentationContext,
        line_no: int,
        kind: str,
    ) -> list[ast.stmt]:
        loop_key = f"{context.qualname}@{line_no}:{kind}"
        probe = _tracker_call(
            context.tracker_name,
            "loop_iteration",
            ast.Constant(value=loop_key),
        )
        if body:
            ast.copy_location(probe, body[0])
        body = self._instrument_statement_list(body, context)
        return [probe, *body]

    def _transform_simple_statement(self, stmt: ast.stmt) -> ast.stmt:
        return stmt

    def _visit_stmt_children(self, stmt: ast.stmt) -> ast.stmt:
        return stmt

    def _visit_expr(self, node):  # type: ignore[no-untyped-def]
        return node

    def _visit_with_item(self, item):  # type: ignore[no-untyped-def]
        return item

    def _split_module_prologue(self, body: list[ast.stmt]) -> tuple[list[ast.stmt], list[ast.stmt]]:
        index = 0
        if index < len(body) and _is_docstring_statement(body[index]):
            index += 1
        while index < len(body) and _is_future_import(body[index]):
            index += 1
        return body[:index], body[index:]

    def _split_body_prologue(
        self,
        body: list[ast.stmt],
        *,
        preserve_docstring: bool,
    ) -> tuple[list[ast.stmt], list[ast.stmt]]:
        index = 0
        if preserve_docstring and index < len(body) and _is_docstring_statement(body[index]):
            index += 1
        return body[:index], body[index:]

    def _body_insert_index(self, body: list[ast.stmt], *, preserve_docstring: bool) -> int:
        if preserve_docstring and body and _is_docstring_statement(body[0]):
            return 1
        return 0


def instrument_tree(tree: ast.Module, tracker_name: str = "_big_o_tracker") -> ast.Module:
    return InstrumentationInjector(tracker_name=tracker_name).instrument(tree)


__all__ = ["InstrumentationContext", "InstrumentationInjector", "instrument_tree"]
