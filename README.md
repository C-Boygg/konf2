# Граф зависимостей Cargo · вариант 15

Программа читает открытый sparse-индекс Cargo напрямую по HTTP(S). Для чтения индекса, разбора JSON и построения графа хватает стандартной библиотеки Python. PNG рисует Graphviz.

## Запуск

Нужны Python 3.9+ и Graphviz с командой `dot` в `PATH`. [Загрузка Graphviz](https://graphviz.org/download/)

```powershell
python main.py --help
python main.py --package regex --repository https://index.crates.io --depth 3 --output graph.png --ascii
```

| Опция | Значение |
| --- | --- |
| `--package` | Имя корневого пакета, обязательный параметр |
| `--repository` | URL sparse-индекса (по умолчанию crates.io) или путь к JSON с `--test` |
| `--test` | Читать тестовый репозиторий из JSON |
| `--output` | Файл PNG, по умолчанию `graph.png`. Рядом сохраняется одноимённый DOT |
| `--ascii` | Дополнительно напечатать дерево в консоли |
| `--depth` | Максимальное число рёбер от корня, по умолчанию 3. Глубина 0 оставляет только корень |

## Проверка этапов

### 1. Параметры CLI

В коммите `6318009` команда `python main.py --package regex` выводит:

```text
package=regex
repository=https://index.crates.io
test=False
output=graph.png
ascii=False
depth=3
```

Каждая строка ниже дописывается после `python main.py`. Ожидаемый код выхода для каждой ошибки — `2`.

| Аргументы | Ошибка |
| --- | --- |
| `--package !` | Неправильное имя пакета |
| `--package A --repository bad` | Ожидается HTTP(S) URL |
| `--package A --test` | Тестовый файл не найден |
| `--package A --test=maybe` | Флаг `--test` не принимает значение |
| `--package A --output graph.svg` | Требуется расширение `.png` |
| `--package A --ascii=maybe` | Флаг `--ascii` не принимает значение |
| `--package A --depth -1` | Глубина должна быть неотрицательной |
| `--package A --depth x` | Глубина должна быть целым числом |

### 2. Прямые зависимости

В коммите `18e004c` команда `python main.py --package regex --repository https://index.crates.io` напечатала версию `1.13.1` и все записи её поля `deps`. Среди них обычные зависимости `aho-corasick`, `memchr`, `regex-automata`, `regex-syntax` и зависимости разработки `anyhow`, `doc-comment`, `env_logger`, `quickcheck`, `regex-test`. Несуществующий пакет завершил работу с сообщением об ошибке и кодом `1`. [Формат индекса Cargo](https://doc.rust-lang.org/cargo/reference/registry-index.html)

### 3. DFS и тестовый репозиторий

Файл [repository.json](examples/repository.json) задаёт для каждого пакета список непосредственных зависимостей. Имена состоят из заглавных латинских букв. Пакет без зависимостей задаётся пустым списком.

```powershell
python main.py --test --repository examples/repository.json --package A --depth 3 --ascii
python main.py --test --repository examples/repository.json --package H --depth 3 --ascii
python main.py --test --repository examples/repository.json --package G --depth 0 --ascii
```

- У `A` ветки через `B` и `C` сходятся в `E`, петля `D → D` помечается как `[cycle]`, а на глубине 3 обход останавливается.
- От `H` пакет `E` впервые достигается по пути `H → A → B → E`. DFS возвращается к нему по короткому пути `H → E` и добавляет рёбра `E → F` и `F → B`.
- Для `G` на глубине 0 выводится только `G`.

В коммите `e545818` те же команды без `--ascii` показывают граф списком смежности.

### 4. Обратные зависимости

Режим `--reverse` доступен в коммите четвёртого этапа `41a1908`.

```powershell
python main.py --test --repository examples/repository.json --reverse --package E --depth 1
python main.py --test --repository examples/repository.json --reverse --package E --depth 3
python main.py --test --repository examples/repository.json --reverse --package G
```

На глубине 1 выводится `B, C, H`. На глубине 3 выводится `B, A, H, F, C`. Для `G` выводится `Обратных зависимостей нет`. Рёбра разворачиваются перед запуском того же DFS. Корневой пакет исключается из списка, даже если цикл ведёт обратно к нему.

### 5. Визуализация

```powershell
python main.py --package regex --depth 3 --output examples/regex.png --ascii
python main.py --package syn --depth 3 --output examples/syn.png --ascii
python main.py --package memchr --depth 3 --output examples/memchr.png --ascii
```

| Пакет | PNG | DOT |
| --- | --- | --- |
| `regex 1.13.1` | [PNG](examples/regex.png) | [DOT](examples/regex.dot) |
| `syn 3.0.10` | [PNG](examples/syn.png) | [DOT](examples/syn.dot) |
| `memchr 2.8.3` | [PNG](examples/memchr.png) | [DOT](examples/memchr.dot) |

Корень выбирается по последней стабильной версии. Для каждого ребра выбирается наибольшая версия из того же индекса, которая удовлетворяет требованию SemVer и доступна для новых установок. Программа включает обычные зависимости и зависимости сборки для всех платформ. Зависимости разработки и опциональные зависимости пропускаются. Флаги features и `Cargo.lock` не учитываются. [Правила выбора версий Cargo](https://doc.rust-lang.org/cargo/reference/resolver.html)

#### Сравнение с Cargo

Для каждого примера создаётся временный проект Cargo с пустым `src/lib.rs` и одной зависимостью. Версия фиксируется через `=`, как в этом примере для `regex`.

```toml
[package]
name = "compare-graphs"
version = "0.1.0"
edition = "2021"

[dependencies]
regex = "=1.13.1"
```

```powershell
cargo tree --target all --edges normal,build --package regex --depth 3 --charset ascii --no-dedupe
```

Для `syn` и `memchr` команда повторяется с соответствующим именем пакета и версией из таблицы. [Параметры cargo tree](https://doc.rust-lang.org/cargo/commands/cargo-tree.html)

Результат запуска `cargo tree` с Cargo 1.100.0:

```text
regex v1.13.1
|-- aho-corasick v1.1.5
|   `-- memchr v2.8.3
|-- memchr v2.8.3
|-- regex-automata v0.4.18
|   |-- aho-corasick v1.1.5
|   |   `-- memchr v2.8.3
|   |-- memchr v2.8.3
|   `-- regex-syntax v0.8.11
`-- regex-syntax v0.8.11

syn v3.0.10
|-- proc-macro2 v1.0.107
|   `-- unicode-ident v1.0.27
|-- quote v1.0.47
|   `-- proc-macro2 v1.0.107
|       `-- unicode-ident v1.0.27
`-- unicode-ident v1.0.27

memchr v2.8.3
```

| Пакет | Рёбер в DOT | Уникальных рёбер в Cargo | Объяснение |
| --- | ---: | ---: | --- |
| `regex` | 2 | 8 | В Cargo стандартная feature `perf` включает `perf-literal`. Она добавляет `aho-corasick` и `memchr`, а также включает `regex-automata/perf-literal`. Feature `syntax` пакета `regex-automata` добавляет его ребро к `regex-syntax`. |
| `syn` | 3 | 5 | Cargo включает стандартную feature `printing`, которая добавляет `quote`. У `quote` есть зависимость от `proc-macro2`. |
| `memchr` | 0 | 0 | При стандартных features у обеих программ граф состоит из одного пакета. |

Версии пакетов на общих рёбрах совпали. Cargo показывает один пакет в нескольких ветках дерева, а DOT хранит его как одну вершину. Cargo использовался только для этого сравнения. [Features в Cargo](https://doc.rust-lang.org/cargo/reference/features.html)

## Автоматические проверки

```powershell
python -m unittest -v
```
