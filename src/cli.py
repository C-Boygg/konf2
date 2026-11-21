import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit


DEFAULT_DEPTH = 3
REAL_PACKAGE = r"[A-Za-z0-9][A-Za-z0-9_-]*"
TEST_PACKAGE = r"[A-Z]+"


def valid_url(repository):
    try:
        url = urlsplit(repository.removeprefix("sparse+"))
        url.port
    except ValueError:
        return False
    return all((
        url.scheme in {"http", "https"},
        url.hostname,
        not url.query,
        not url.fragment,
        not any(char.isspace() for char in repository),
    ))


def check_repository(parser, args):
    if args.test:
        if not Path(args.repository).is_file():
            parser.error("--repository: тестовый файл не найден")
    elif not valid_url(args.repository):
        parser.error("--repository: ожидается HTTP(S) URL индекса Cargo")


def check_output(parser, args):
    invalid = any((
        args.output.suffix.lower() != ".png",
        args.output.is_dir(),
        not args.output.parent.is_dir(),
    ))
    if invalid:
        parser.error("--output: укажите имя файла .png в существующей папке")
    if args.test:
        source = Path(args.repository).resolve()
        targets = (
            args.output.resolve(),
            args.output.with_suffix(".dot").resolve(),
        )
        if source in targets:
            parser.error("--output: файл совпадает с тестовым репозиторием")


def create_parser():
    parser = argparse.ArgumentParser(description="Граф зависимостей Cargo")
    parser.add_argument("--package", required=True, help="имя пакета")
    parser.add_argument(
        "--repository", default="https://index.crates.io",
        help="URL индекса или путь к JSON",
    )
    parser.add_argument(
        "--test", action="store_true", help="читать тестовый JSON",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("graph.png"),
        help="имя файла PNG",
    )
    parser.add_argument(
        "--ascii", action="store_true", help="напечатать ASCII-дерево",
    )
    parser.add_argument(
        "--depth", type=int, default=DEFAULT_DEPTH,
        help="максимальная глубина",
    )
    return parser


def parse_args():
    parser = create_parser()
    args = parser.parse_args()
    pattern = TEST_PACKAGE if args.test else REAL_PACKAGE
    if not re.fullmatch(pattern, args.package):
        parser.error("--package: неправильное имя пакета")
    check_repository(parser, args)
    check_output(parser, args)
    if args.depth < 0:
        parser.error("--depth: глубина должна быть неотрицательной")
    return parser, args
