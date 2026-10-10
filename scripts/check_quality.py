"""Проверяет длину строк, ветвления и числовые сравнения в src."""

import ast
from pathlib import Path


MAX_LINE_LENGTH = 80
MAX_COMPLEXITY = 10
ROOT = Path(__file__).resolve().parents[1]
BRANCH_TYPES = (ast.If, ast.For, ast.While, ast.IfExp, ast.ExceptHandler)


def branch_weight(node):
    """Считает независимые ветвления одного узла синтаксического дерева."""
    if isinstance(node, BRANCH_TYPES):
        return 1
    if isinstance(node, ast.BoolOp):
        return len(node.values) - 1
    if isinstance(node, ast.comprehension):
        return 1 + len(node.ifs)
    return 0


def complexity(function):
    """Оценивает сложность функции по управляющим конструкциям."""
    return 1 + sum(branch_weight(node) for node in ast.walk(function))


def line_issues(path, source):
    """Находит строки длиннее установленного предела."""
    return [
        f'{path}:{number}: длина строки {len(line)}'
        for number, line in enumerate(source.splitlines(), 1)
        if len(line) > MAX_LINE_LENGTH
    ]


def numeric_comparison(node):
    """Определяет числовые литералы в непосредственных сравнениях."""
    if not isinstance(node, ast.Compare):
        return False
    return any(
        isinstance(operand, ast.Constant)
        and type(operand.value) in (int, float)
        for operand in [node.left, *node.comparators]
    )


def tree_issues(path, tree):
    """Проверяет сложность функций и числовые сравнения."""
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            score = complexity(node)
            if score > MAX_COMPLEXITY:
                issues.append(
                    f'{path}:{node.lineno}: сложность {node.name} = {score}'
                )
        if numeric_comparison(node):
            issues.append(f'{path}:{node.lineno}: число в сравнении')
    return issues


def main():
    """Печатает результат проверки и возвращает код завершения."""
    issues = []
    maximum = 0
    for path in sorted((ROOT / 'src').glob('*.py')):
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        relative = path.relative_to(ROOT)
        issues.extend(line_issues(relative, source))
        issues.extend(tree_issues(relative, tree))
        scores = [
            complexity(node) for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]
        maximum = max([maximum, *scores])
    if issues:
        print('\n'.join(issues))
        return 1
    print(f'OK: длина строк <= {MAX_LINE_LENGTH}.')
    print(f'OK: максимальная сложность функций = {maximum}.')
    print('OK: числовых литералов в сравнениях нет.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
