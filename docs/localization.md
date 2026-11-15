# Localization

The text Sonolus shows for Minimai is in [`localization.toml`](../localization.toml) at the repo root: the options' titles, descriptions and select values, the option categories, and the tutorial's messages. Each text is a table by locale:

```toml
[options.tap_speed]
title.en = "Tap Speed"
title.ja = "タップスピード"
description.en = "…"

[options.orientation.values]
landscape.en = "Landscape"
landscape.ja = "横向き"

[categories.challenge]
title.en = "Challenge"

[instructions.intro]
text.en = "Hello! I'll show you how to play!"
```

| Table | Keys |
|---|---|
| `[options.<field>]` | `title`, `description`, for an option of `Options` (`lib/options.py`) |
| `[options.<field>.values]` | one text per value id of a select option |
| `[categories.<field>]` | `title`, for an `OptionCategory` of `Options` |
| `[instructions.<field>]` | `text`, for an `Instruction` of `Instructions` (`tutorial/instructions.py`) |

The locales are Sonolus': `el`, `en`, `es`, `fr`, `id`, `it`, `ja`, `ko`, `pt`, `ru`, `tr`, `vi`, `zhs`, `zht`. Every text needs `en`, and it's written first; the others are optional. Sonolus shows the player's language, or else their fallback language. A text with only `en` is shown as it is in every language.

Standard texts (`StandardText.SPEED`, `StandardText.OFF`, …) are translated by Sonolus and have no entry. An option with a standard name has no title, and a select value that is a standard text has no value text.

The build stops on a missing `en` text, an unknown locale or key, an entry for an option, value, category or instruction that doesn't exist, or an option that sets its title or description in code.

## Adding a locale

Add `<key>.<locale> = "…"` lines beside the `en` ones. Text left out shows in the player's fallback language. `python main.py localization` lists, for each locale that has some text, what it still lacks (`python main.py localization vi` for one locale). Text without letters, such as the Mirror arrows, needs no translation.

## In code

An option keeps its English `name`, which Sonolus uses to keep its value, and gives no `title` or `description`. A select option's `values` are ids (`"landscape"`), or standard texts. `Options` is decorated with `@localized_options` and `Instructions` with `@localized_instructions` (`minimai/localization.py`), in place of sonolus.py's `@options` and `@instructions`.
