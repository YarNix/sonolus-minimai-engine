"""Text shown in Sonolus, from ``localization.toml`` (docs/localization.md)."""

import tomllib
from dataclasses import fields, is_dataclass, replace
from pathlib import Path
from typing import Any, dataclass_transform, get_args

from sonolus.script.instruction import Instruction, instruction, instructions
from sonolus.script.metadata import Locale, encode_localization_text
from sonolus.script.options import OptionCategory, options

LOCALIZATION_PATH = Path(__file__).parents[1] / "localization.toml"
LOCALES = frozenset(get_args(Locale.__value__))
TABLES = {"options", "categories", "instructions"}
OPTION_KEYS = {"title", "description", "values"}


def load_localization() -> dict[str, Any]:
    data = tomllib.loads(LOCALIZATION_PATH.read_text(encoding="utf-8"))
    unknown = set(data) - TABLES
    if unknown:
        raise ValueError(f"{LOCALIZATION_PATH.name}: unknown tables {sorted(unknown)}")
    return data


def encoded(text: Any, where: str) -> str:
    """A table of text by locale, as Sonolus reads it: plain text when there's only English."""
    if not isinstance(text, dict) or not text:
        raise ValueError(f"{LOCALIZATION_PATH.name}: {where} must be a table of text by locale")
    unknown = set(text) - LOCALES
    if unknown:
        raise ValueError(f"{LOCALIZATION_PATH.name}: {where} has unknown locales {sorted(unknown)}")
    if "en" not in text:
        raise ValueError(f"{LOCALIZATION_PATH.name}: {where} has no en text")
    if not all(isinstance(value, str) for value in text.values()):
        raise ValueError(f"{LOCALIZATION_PATH.name}: {where} must be text")
    if set(text) == {"en"}:
        return text["en"]
    # English first: the usual fallback language.
    return encode_localization_text({"en": text["en"], **text})


def is_standard(text: Any) -> bool:
    """Standard texts (``#OFF``, ``#SPEED``, …) are translated by Sonolus."""
    return isinstance(text, str) and text.startswith("#")


def check_used(table: dict[str, Any], used: set[str], kind: str):
    unused = set(table) - used
    if unused:
        raise ValueError(f"{LOCALIZATION_PATH.name}: [{kind}] has entries for {sorted(unused)}, which don't exist")


@dataclass_transform(kw_only_default=True)
def localized_options[T](cls: type[T]) -> T:
    """``@options``, with the titles, descriptions and select values' text from ``[options]``, and the category
    titles from ``[categories]``. The class gives each select value an id and leaves out its own text."""
    data = load_localization()
    texts, category_texts = data.get("options", {}), data.get("categories", {})

    renamed: dict[int, OptionCategory] = {}
    for key, category in list(vars(cls).items()):
        if isinstance(category, OptionCategory) and key in category_texts:
            renamed[id(category)] = replace(category, title=encoded(category_texts[key]["title"], f"{key}.title"))
            setattr(cls, key, renamed[id(category)])
    check_used(
        category_texts, {key for key, value in vars(cls).items() if isinstance(value, OptionCategory)}, "categories"
    )

    found = set()
    for key, option in vars(cls).items():
        if not is_dataclass(option) or not {"name", "title", "description"} <= {f.name for f in fields(option)}:
            continue
        found.add(key)
        if option.title is not None or option.description is not None:
            raise ValueError(f"{cls.__name__}.{key}: its title and description go in {LOCALIZATION_PATH.name}")
        if id(option.category) in renamed:
            option.category = renamed[id(option.category)]
        entry = texts.get(key, {})
        unknown = set(entry) - OPTION_KEYS
        if unknown:
            raise ValueError(f"{LOCALIZATION_PATH.name}: options.{key} has unknown keys {sorted(unknown)}")
        if "title" in entry:
            option.title = encoded(entry["title"], f"options.{key}.title")
        elif not is_standard(option.name):
            raise ValueError(f"{LOCALIZATION_PATH.name}: options.{key} has no title")
        if "description" in entry:
            option.description = encoded(entry["description"], f"options.{key}.description")
        if hasattr(option, "values"):
            values = entry.get("values", {})
            check_used(values, set(option.values), f"options.{key}.values")
            option.values = [
                value if is_standard(value) else encoded(values.get(value), f"options.{key}.values.{value}")
                for value in option.values
            ]
        elif "values" in entry:
            raise ValueError(f"{LOCALIZATION_PATH.name}: options.{key} has values but isn't a select option")
    check_used(texts, found, "options")
    return options(cls)


@dataclass_transform(kw_only_default=True)
def localized_instructions[T](cls: type[T]) -> T:
    """``@instructions``, with each ``Instruction`` field's text from ``[instructions]``."""
    texts = load_localization().get("instructions", {})
    found = set()
    for key, annotation in cls.__annotations__.items():
        if annotation is Instruction and key not in vars(cls):
            found.add(key)
            if key not in texts:
                raise ValueError(f"{LOCALIZATION_PATH.name}: instructions.{key} is missing")
            setattr(cls, key, instruction(encoded(texts[key]["text"], f"instructions.{key}.text")))
    check_used(texts, found, "instructions")
    return instructions(cls)


def texts(table: dict[str, Any], prefix: str = "") -> dict[str, dict[str, str]]:
    """Every text in a table of ``localization.toml``, by its dotted key."""
    result = {}
    for key, value in table.items():
        if isinstance(value, dict) and value and set(value) <= LOCALES:
            result[f"{prefix}{key}"] = value
        elif isinstance(value, dict):
            result |= texts(value, f"{prefix}{key}.")
    return result


def report(locales: list[str]):
    """``main.py localization``: how much of the text each locale has, and what it lacks."""
    # Text without letters (the Mirror arrows) reads the same in every locale.
    every = {key: text for key, text in texts(load_localization()).items() if any(c.isalpha() for c in text["en"])}
    present = sorted({locale for text in every.values() for locale in text} - {"en"})
    for locale in locales or present:
        missing = [key for key, text in every.items() if locale not in text]
        print(f"{locale}: {len(every) - len(missing)} of {len(every)} texts")
        for key in missing:
            print(f"  {key}")
