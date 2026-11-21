import json
from functools import cache
from http import HTTPStatus
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .versions import matches, version_key


SHORT_NAME_LENGTH = 2
MEDIUM_NAME_LENGTH = 3
PREFIX_LENGTH = 2
PREFIX_END = 4
REQUEST_TIMEOUT = 15


def index_path(package):
    name = package.lower()
    if len(name) <= SHORT_NAME_LENGTH:
        return f"{len(name)}/{name}"
    if len(name) == MEDIUM_NAME_LENGTH:
        return f"3/{name[0]}/{name}"
    return f"{name[:PREFIX_LENGTH]}/{name[PREFIX_LENGTH:PREFIX_END]}/{name}"


class CargoIndex:
    def __init__(self, url):
        self.url = url.removeprefix("sparse+").rstrip("/")

    @cache
    def versions(self, package):
        path = index_path(package)

        try:
            url = f"{self.url}/{path}"
            with urlopen(url, timeout=REQUEST_TIMEOUT) as response:
                rows = [json.loads(line) for line in response if line.strip()]
        except HTTPError as error:
            if error.code == HTTPStatus.NOT_FOUND:
                raise ValueError(f"Пакет {package} не найден") from error
            message = f"Индекс Cargo вернул HTTP {error.code}"
            raise ValueError(message) from error
        except (URLError, TimeoutError) as error:
            message = f"Не удалось прочитать индекс Cargo: {error}"
            raise ValueError(message) from error

        return [row for row in rows if not row["yanked"]]

    @cache
    def select(self, package, requirement="*"):
        candidates = [
            row for row in self.versions(package)
            if matches(row["vers"], requirement)
        ]
        if not candidates:
            message = (
                f"У пакета {package} нет подходящей версии ({requirement})"
            )
            raise ValueError(message)
        row = max(candidates, key=lambda row: version_key(row["vers"]))
        return row["name"], row["vers"]

    def dependencies(self, node):
        package, version = node
        row = next(
            row for row in self.versions(package) if row["vers"] == version
        )
        result = []
        for dep in row["deps"]:
            if dep["kind"] == "dev" or dep["optional"]:
                continue
            registry = dep.get("registry")
            registry_url = (registry or "").removeprefix("sparse+").rstrip("/")
            if registry_url and registry_url != self.url:
                message = (
                    f"Зависимость {dep['name']} находится в другом индексе: "
                    f"{registry}"
                )
                raise ValueError(message)
            name = dep.get("package") or dep["name"]
            result.append(self.select(name, dep["req"]))
        return result
