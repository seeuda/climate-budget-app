# Repo Hygiene Report

Date: 2026-04-14

## Summary

Repository root currently contains several files that look duplicated, misnamed, or likely temporary artifacts.

## Findings

1. **Binary file with markdown extension**
   - `README.md` starts with Python bytecode magic bytes (`0xCB 0x0D 0x0D 0x0A`) and cannot be decoded as UTF-8 text.
   - This is usually a sign of a misplaced `.pyc`-like artifact.

2. **Likely accidental duplicate / temporary files**
   - `config_x.json` is byte-identical to the current `README.md` binary file.
   - `test_keyword_regression (5).py` is byte-identical to `check_duplicate_ids.py`.

3. **Root/data naming mismatch suggests clutter**
   - `check_duplicate_ids_x.py` content is JSON and closely matches `data/keyword_dictionary.json`.
   - `keyword_dictionary.json` content looks like logic mapping data and overlaps with `data/logic_mapping.json` naming-wise.
   - `logic_mapping.json` in root is TOML-style content (theme config), not logic mapping JSON.

4. **Source of truth appears to be `data/` directory**
   - Active scripts reference `data/keyword_dictionary.json`, `data/config.json`, and `data/logic_mapping.json` paths.
   - This implies many similarly named root files are likely legacy/debug copies.

## Suggested Cleanup Plan (safe order)

1. Keep `data/` as canonical dataset location.
2. Move suspicious root artifacts into an `archive/` folder first (do not immediately delete).
3. Restore a real text `README.md`.
4. Rename misleading files to their actual content type (e.g., `.toml`, `.pyc`, `.json`).
5. Add a lightweight CI check to detect binary content in `.md` and `.json` files.

