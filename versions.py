import re


def version_key(version):
    number, _, pre = version.split("+", 1)[0].partition("-")
    identifiers = tuple((0, int(part)) if part.isdigit() else (1, part) for part in pre.split("."))
    return tuple(map(int, number.split("."))), not pre, identifiers if pre else ()


def matches(version, requirement):
    key = version_key(version)
    prerelease_allowed = key[1]
    for item in requirement.split(","):
        item = item.strip()
        if item in {"*", "x", "X"}:
            continue
        match = re.fullmatch(r"(\^|~|>=|<=|>|<|=)?\s*(\d+(?:\.\d+){0,2})(\.\*|\.[xX])?(-[\w.-]+)?(?:\+[\w.-]+)?", item)
        if not match:
            raise ValueError(f"Неизвестное требование к версии: {item}")
        operator, number, wildcard, pre = match.groups()
        parts = number.split(".")
        size = len(parts)
        minimum = version_key(".".join(parts + ["0"] * (3 - size)) + (pre or ""))
        same_prefix = key[0][:size] == minimum[0][:size]
        prerelease_allowed |= bool(pre and key[0] == minimum[0])
        if wildcard or operator == "=":
            valid = same_prefix and (size < 3 or key == minimum)
        elif operator == ">":
            valid = key > minimum and (size == 3 or not same_prefix)
        elif operator == ">=":
            valid = key >= minimum or (size < 3 and same_prefix)
        elif operator == "<":
            valid = key < minimum and (size == 3 or not same_prefix)
        elif operator == "<=":
            valid = key <= minimum or (size < 3 and same_prefix)
        else:
            if operator == "~":
                fixed = min(size, 2)
            else:
                fixed = next((i + 1 for i, part in enumerate(parts) if int(part)), size)
            valid = key >= minimum and key[0][:fixed] == minimum[0][:fixed]
        if not valid:
            return False
    return prerelease_allowed
