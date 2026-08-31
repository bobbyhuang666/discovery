# Example: Quick Build

**User:** Write a VBA macro that scans every workbook in a folder and extracts purchase item, quantity, unit price, total, note, invoice status, and file date.

**Correct route:** Build / Quick.

**Inspect first:** Existing workbook layout or provided sample files, if available.

**Decision:** How should rows with missing or differently named fields be handled?

**Recommended question:**

> **Recommendation:** Keep the row, leave missing values blank, and add a `source_file` plus `warning` column. This preserves traceability and avoids silently dropping purchases. Choose strict rejection only if downstream accounting cannot accept partial rows. Should I use the tolerant approach?

**Stop after:** Folder/runtime, source-sheet detection, output columns, duplicate behavior, missing-field behavior, date source, and one acceptance example are clear.

**Bad behavior:** Ask about market size, willingness to pay, personas, retention, or a full roadmap.
