import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit


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


def main():
    _, args = parse_args()
    for key, value in vars(args).items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
