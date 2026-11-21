import operator
import re


VERSION_PARTS = 3
TILDE_PREFIX_LENGTH = 2
REQUIREMENT_PATTERN = (
    r"(\^|~|>=|<=|>|<|=)?\s*"
    r"(\d+(?:\.\d+){0,2})(\.\*|\.[xX])?"
    r"(-[\w.-]+)?(?:\+[\w.-]+)?"
)
COMPARISONS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


def version_key(version):
    number, _, pre = version.split("+", 1)[0].partition("-")
    identifiers = tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in pre.split(".")
    )
    return (
        tuple(map(int, number.split("."))),
        not pre,
        identifiers if pre else (),
    )


def parse_requirement(item):
    match = re.fullmatch(REQUIREMENT_PATTERN, item)
    if not match:
        raise ValueError(f"Неизвестное требование к версии: {item}")
    operation, number, wildcard, pre = match.groups()
    parts = number.split(".")
    padded = parts + ["0"] * (VERSION_PARTS - len(parts))
    minimum = version_key(".".join(padded) + (pre or ""))
    return operation, parts, wildcard, pre, minimum


def comparison_matches(key, minimum, operation, size):
    same_prefix = key[0][:size] == minimum[0][:size]
    if size == VERSION_PARTS:
        return COMPARISONS[operation](key, minimum)
    if same_prefix:
        return operation in {">=", "<="}
    return COMPARISONS[operation](key, minimum)


def compatible_matches(key, minimum, operation, parts):
    if operation == "~":
        fixed = min(len(parts), TILDE_PREFIX_LENGTH)
    else:
        fixed = next(
            (i + 1 for i, part in enumerate(parts) if int(part)),
            len(parts),
        )
    return key >= minimum and key[0][:fixed] == minimum[0][:fixed]


def requirement_matches(key, requirement):
    operation, parts, wildcard, _, minimum = requirement
    size = len(parts)
    if wildcard or operation == "=":
        same_prefix = key[0][:size] == minimum[0][:size]
        return same_prefix and (size < VERSION_PARTS or key == minimum)
    if operation in COMPARISONS:
        return comparison_matches(key, minimum, operation, size)
    return compatible_matches(key, minimum, operation, parts)


def matches(version, requirement):
    key = version_key(version)
    prerelease_allowed = key[1]
    for item in requirement.split(","):
        item = item.strip()
        if item in {"*", "x", "X"}:
            continue
        parsed = parse_requirement(item)
        _, _, _, pre, minimum = parsed
        prerelease_allowed |= bool(pre and key[0] == minimum[0])
        if not requirement_matches(key, parsed):
            return False
    return prerelease_allowed
