from .cargo import CargoIndex
from .cli import parse_args
from .graph import build_graph, print_tree, read_test_repository, save_graph


def main():
    parser, args = parse_args()
    try:
        if args.test:
            repo = read_test_repository(args.repository)
            if args.package not in repo:
                raise ValueError(f"Пакет {args.package} не найден")
            root = args.package
            dependencies = repo.__getitem__
        else:
            index = CargoIndex(args.repository)
            root = index.select(args.package)
            dependencies = index.dependencies
        graph = build_graph(root, dependencies, args.depth)
        save_graph(graph, args.output)
        if args.ascii:
            print_tree(root, graph, args.depth)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Ошибка: {error}\n")


if __name__ == "__main__":
    main()
