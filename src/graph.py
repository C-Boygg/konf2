import json
import re
import subprocess
from pathlib import Path


def read_test_repository(filename):
    repo = json.loads(Path(filename).read_text(encoding="utf-8-sig"))
    if not isinstance(repo, dict):
        raise ValueError("Тестовый репозиторий должен быть JSON-объектом")
    for name, deps in repo.items():
        if not re.fullmatch(r"[A-Z]+", name) or not isinstance(deps, list):
            raise ValueError(f"Неверная запись о пакете {name}")
        if any(not isinstance(dep, str) or dep not in repo for dep in deps):
            raise ValueError(f"У пакета {name} есть неизвестная зависимость")
    return repo


def build_graph(root, dependencies, max_depth):
    graph = {}
    depths = {}
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if node in depths and depths[node] <= depth:
            continue
        depths[node] = depth
        if depth == max_depth:
            graph[node] = []
            continue
        graph[node] = list(dict.fromkeys(dependencies(node)))
        stack.extend((child, depth + 1) for child in reversed(graph[node]))
    return graph


def label(node):
    return " ".join(node) if isinstance(node, tuple) else node


def print_tree(root, graph, max_depth):
    stack = [(root, "", "", [])]
    while stack:
        node, prefix, branch, parents = stack.pop()
        cycle = node in parents
        print(prefix + branch + label(node) + (" [cycle]" if cycle else ""))
        if cycle or len(parents) == max_depth:
            continue
        if branch:
            prefix += "    " if branch == "`-- " else "|   "
        children = graph[node]
        for i, child in reversed(list(enumerate(children))):
            branch = "`-- " if i == len(children) - 1 else "|-- "
            stack.append((child, prefix, branch, parents + [node]))


def save_graph(graph, output):
    dot = output.with_suffix(".dot")
    lines = ["digraph dependencies {", "    rankdir=LR;"]
    for node, children in graph.items():
        source = json.dumps(label(node))
        lines.append(f"    {source};")
        for child in children:
            lines.append(f"    {source} -> {json.dumps(label(child))};")
    lines.append("}")
    dot.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        command = ["dot", "-Tpng", "-o", str(output), str(dot)]
        subprocess.run(command, check=True)
    except FileNotFoundError as error:
        raise ValueError("Установите Graphviz и добавьте dot в PATH") from error
    except subprocess.CalledProcessError as error:
        raise ValueError("Graphviz не смог сохранить PNG") from error
    print(f"DOT: {dot}")
    print(f"PNG: {output}")
