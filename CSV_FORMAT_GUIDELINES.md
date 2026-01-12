CSV format guidelines
=====================

Baseline rules
--------------
- Encoding: UTF-8 (no BOM).
- Delimiter: ASCII comma `,`.
- Quoting: optional double quotes; escape embedded quotes as `""`.
- Whitespace: ignore leading/trailing ASCII spaces and tabs around each field.
- Empty fields: skip after trimming; do not emit empty tokens.
- Comments: none (or treat lines starting with `#` as comments if desired).
- Newlines: accept `\n` and `\r\n`.

Chinese-specific
----------------
- Accept both ASCII comma `,` and Chinese comma `，` as separators.
- Trim ASCII spaces/tabs and full-width space (`\u3000`) around tokens.
- Ignore empty tokens after trimming.

English-specific
----------------
- Standard CSV quoting: commas inside quotes are part of the field.
- Trim ASCII whitespace outside quotes; preserve inner spaces.

Examples
--------
- Chinese lines:
  - `苹果, 梨，香蕉 , 橙子` → tokens: `苹果`, `梨`, `香蕉`, `橙子`
  - `"长城",   北京，"天津"` → tokens: `长城`, `北京`, `天津`
- English lines:
  - `apple, pear, banana, orange` → tokens: `apple`, `pear`, `banana`, `orange`
  - `"New York", "San Francisco", Seattle` → tokens: `New York`, `San Francisco`, `Seattle`

FAQ
---
- Is there always a whitespace after a comma? No. CSV does not require spaces after delimiters. Parsing should accept both `a,b` and `a, b` (and, for Chinese, `a，b` / `a， b`) by trimming optional surrounding whitespace.
