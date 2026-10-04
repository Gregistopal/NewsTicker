# NewsTicker version collection

Collected on October 2, 2026 from Downloads. This folder contains 10 releases, 11 ZIP archives, and 11 extracted copies. The Downloads originals remain in place.

Each release is under `versions/<version>/`. `archives/` holds the original ZIP downloads. `extracted/` holds the complete extracted package, including its runtime, settings, logs, and backups. A redundant outer download folder was removed from the copied layout; package contents were preserved.

## Versions

| Release | Recorded build date | ZIP archives | Extracted copies |
| --- | --- | ---: | ---: |
| [1.0.0](versions/1.0.0/) | 2026-09-25 | 1 | 1 |
| [1.0.1](versions/1.0.1/) | 2026-09-25 | 1 | 1 |
| [1.0.2](versions/1.0.2/) | 2026-09-25 | 1 | 1 |
| [1.0.3](versions/1.0.3/) | 2026-09-25 | 1 | 1 |
| [1.0.4](versions/1.0.4/) | 2026-09-25 | 1 | 1 |
| [1.0.5](versions/1.0.5/) | 2026-09-25 | 1 | 1 |
| [1.0.6](versions/1.0.6/) | 2026-09-25 | 1 | 1 |
| [1.0.7](versions/1.0.7/) | 2026-09-25 | 1 | 1 |
| [1.1.0](versions/1.1.0/) | 2026-09-26 | 1 | 1 |
| [1.1.1](versions/1.1.1/) | 2026-09-26 | 2 | 2 |

## The two 1.1.1 copies

The newest release found is 1.1.1. Its two ZIP downloads have identical SHA-256 hashes, and both original filenames were kept. Its two extracted copies have different file contents, so both were preserved:

- `versions/1.1.1/extracted/` came from `Downloads/NewsTicker-1.1.1-Windows/NewsTicker-1.1.1/`.
- `versions/1.1.1/extracted-copy-1/` came from `Downloads/NewsTicker-1.1.1-Windows (1)/NewsTicker-1.1.1/`.

Each has its own settings and data. See [the file differences](inventory/1.1.1-copy-differences.csv). Both retain their original `Start-NewsTicker.cmd` launcher. No application was launched during collection.

## Inventory and verification

All 3,912 copied files were checked against their originals by size and SHA-256 hash. Directory layouts were checked, including empty folders.

- [items.csv](inventory/items.csv): every original download item, copied location, version, build date, size, and verification result.
- [files.csv](inventory/files.csv): every copied file, its original location, size, and SHA-256 hash.
- [collection.json](inventory/collection.json): collection totals, search scope, and identical archive information.

Search scope: Downloads was searched recursively for names containing NewsTicker (including spacing, underscore, and hyphen variants). The current NewsTicker project folder was initially empty. A broader search of the user profile was declined, so other locations are outside this inventory.
