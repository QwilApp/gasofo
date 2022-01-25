import ast
import inspect
import os
import re
import textwrap
from shlex import shlex
from types import FunctionType
from typing import (
    FrozenSet,
    List,
    Optional,
)

USE_OLD_DEP_PARSER = 'GASOFO_USE_OLD_DEP_PARSER' in os.environ


def parse_deps_used_old(method: FunctionType) -> FrozenSet[str]:
    # Start simple for now. Match using regex instead of walking parsed ast tree.
    method_source = discard_comments_and_newlines(textwrap.dedent(inspect.getsource(method)))
    deps_used = re.findall(r'self\.deps\.(.+?)[\(,]', method_source)
    return frozenset(deps_used)


def discard_comments_and_newlines(source: str) -> str:
    lex = shlex(source, posix=True)
    lex.whitespace = '\n'
    return ''.join(lex)


def parse_deps_used_new(method: FunctionType) -> FrozenSet[str]:
    method_source = textwrap.dedent(inspect.getsource(method))
    ast_tree = ast.parse(method_source)
    dep_finder = DepCallFinder()
    dep_finder.visit(ast_tree)
    # print(ast.dump(ast_tree, indent=4))
    return frozenset(dep_finder.deps_calls)


parse_deps_used = parse_deps_used_old if USE_OLD_DEP_PARSER else parse_deps_used_new


class FoundChainedCall(Exception):
    pass


def extract_call_attribute_chain(node: ast.Attribute) -> Optional[List[str]]:
    """
    Attribute(value=Attribute(value=Name(id='self', ...), attr='deps', ...), attrs='x', ...) ==> ['self', 'deps', 'x' ]
    """
    if not isinstance(node, ast.Attribute):
        raise FoundChainedCall()

    if isinstance(node.value, ast.Name):
        return [node.value.id, node.attr]
    else:
        return extract_call_attribute_chain(node.value) + [node.attr]


class DepCallFinder(ast.NodeVisitor):
    def __init__(self):
        self.deps_calls = set()

    def visit_Call(self, node):
        # all deps call starts with "self.deps." so we only need to handle func calls that are referenced via attributes
        if isinstance(node.func, ast.Attribute):
            try:
                attr_chain = extract_call_attribute_chain(node.func)
            except FoundChainedCall:
                self.visit(node.func)
                attr_chain = None

            if attr_chain:
                assert len(attr_chain) > 1  # sanity check
                func_name = attr_chain[-1]
                ref = '.'.join(attr_chain[:-1])

                if ref == 'self.deps':
                    self.deps_calls.add(func_name)

        # Func args could contain more func calls, so make sure we visit args/kwargs too. e.g. a(b=c(), d={'yo': e()})
        for func_arg in node.args:
            self.visit(func_arg)
        for func_kwarg in node.keywords:
            self.visit(func_kwarg)

