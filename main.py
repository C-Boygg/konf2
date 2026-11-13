import argparse
import json
import re
from functools import cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from versions import matches, version_key


def parse_args():
    parser = argparse.ArgumentParser(description="Граф зависимостей Cargo")
    parser.add_argument("--package", required=True, help="имя пакета")
    parser.add_argument("--repository", default="https://index.crates.io", help="URL индекса или путь к JSON")
    parser.add_argument("--test", action="store_true", help="читать тестовый JSON")
    parser.add_argument("--output", type=Path, default=Path("graph.png"), help="имя файла PNG")
    parser.add_argument("--ascii", action="store_true", help="напечатать ASCII-дерево")
    parser.add_argument("--depth", type=int, default=3, help="максимальная глубина")
    parser.add_argument("--reverse", action="store_true", help="обратные зависимости в тестовом режиме")
    args = parser.parse_args()

    if args.reverse and not args.test:
        parser.error("--reverse: нужен режим --test")
    pattern = r"[A-Z]+" if args.test else r"[A-Za-z0-9][A-Za-z0-9_-]*"
    if not re.fullmatch(pattern, args.package):
        parser.error("--package: неправильное имя пакета")
    if args.test:
        if not Path(args.repository).is_file():
            parser.error("--repository: тестовый файл не найден")
    else:
        try:
            url = urlsplit(args.repository.removeprefix("sparse+"))
            valid = (url.scheme in {"http", "https"} and url.hostname and not url.query
                     and not url.fragment and not any(char.isspace() for char in args.repository))
            url.port
        except ValueError:
            valid = False
        if not valid:
            parser.error("--repository: ожидается HTTP(S) URL индекса Cargo")
    if args.output.suffix.lower() != ".png" or args.output.is_dir() or not args.output.parent.is_dir():
        parser.error("--output: укажите имя файла .png в существующей папке")
    if args.depth < 0:
        parser.error("--depth: глубина должна быть неотрицательной")
    return parser, args


class CargoIndex:
    def __init__(self, url):
        self.url = url.removeprefix("sparse+").rstrip("/")

    @cache
    def versions(self, package):
        name = package.lower()
        if len(name) <= 2:
            path = f"{len(name)}/{name}"
        elif len(name) == 3:
            path = f"3/{name[0]}/{name}"
        else:
            path = f"{name[:2]}/{name[2:4]}/{name}"

        try:
            with urlopen(f"{self.url}/{path}", timeout=15) as response:
                rows = [json.loads(line) for line in response if line.strip()]
        except HTTPError as error:
            if error.code == 404:
                raise ValueError(f"Пакет {package} не найден") from error
            raise ValueError(f"Индекс Cargo вернул HTTP {error.code}") from error
        except (URLError, TimeoutError) as error:
            raise ValueError(f"Не удалось прочитать индекс Cargo: {error}") from error

        return [row for row in rows if not row["yanked"]]

    @cache
    def select(self, package, requirement="*"):
        candidates = [row for row in self.versions(package) if matches(row["vers"], requirement)]
        if not candidates:
            raise ValueError(f"У пакета {package} нет подходящей версии ({requirement})")
        row = max(candidates, key=lambda row: version_key(row["vers"]))
        return row["name"], row["vers"]

    def dependencies(self, node):
        package, version = node
        row = next(row for row in self.versions(package) if row["vers"] == version)
        result = []
        for dep in row["deps"]:
            if dep["kind"] == "dev" or dep["optional"]:
                continue
            registry = dep.get("registry")
            index = self if not registry else CargoIndex(registry)
            result.append(index.select(dep.get("package") or dep["name"], dep["req"]))
        return result


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


def reverse_repository(repo):
    result = {name: [] for name in repo}
    for name, children in repo.items():
        for child in children:
            result[child].append(name)
    return result


def main():
    parser, args = parse_args()
    try:
        if args.test:
            repo = read_test_repository(args.repository)
            if args.package not in repo:
                raise ValueError(f"Пакет {args.package} не найден")
            if args.reverse:
                repo = reverse_repository(repo)
            root = args.package
            dependencies = repo.__getitem__
        else:
            index = CargoIndex(args.repository)
            root = index.select(args.package)
            dependencies = index.dependencies
        graph = build_graph(root, dependencies, args.depth)
        if args.reverse:
            packages = [node for node in graph if node != root]
            print(", ".join(packages) or "Обратных зависимостей нет")
            return
        for node, children in graph.items():
            print(f"{label(node)}: {', '.join(map(label, children)) or '-'}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Ошибка: {error}\n")


if __name__ == "__main__":
    main()
