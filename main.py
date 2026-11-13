import argparse
import json
import re
from functools import cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


def parse_args():
    parser = argparse.ArgumentParser(description="Граф зависимостей Cargo")
    parser.add_argument("--package", required=True, help="имя пакета")
    parser.add_argument("--repository", default="https://index.crates.io", help="URL индекса или путь к JSON")
    parser.add_argument("--test", action="store_true", help="читать тестовый JSON")
    parser.add_argument("--output", type=Path, default=Path("graph.png"), help="имя файла PNG")
    parser.add_argument("--ascii", action="store_true", help="напечатать ASCII-дерево")
    parser.add_argument("--depth", type=int, default=3, help="максимальная глубина")
    args = parser.parse_args()

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

    def latest(self, package):
        stable = [row for row in self.versions(package) if "-" not in row["vers"].split("+")[0]]
        if not stable:
            raise ValueError(f"У пакета {package} нет стабильных версий")
        return max(stable, key=lambda row: tuple(map(int, row["vers"].split("+")[0].split("."))))


def main():
    parser, args = parse_args()
    if args.test:
        parser.error("--test: тестовый репозиторий появится на этапе 3")
    try:
        row = CargoIndex(args.repository).latest(args.package)
        print(f"{row['name']} {row['vers']}")
        if not row["deps"]:
            print("Прямых зависимостей нет")
        for dep in row["deps"]:
            print(f"{dep.get('package') or dep['name']} {dep['req']} ({dep['kind'] or 'normal'})")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Ошибка: {error}\n")


if __name__ == "__main__":
    main()
