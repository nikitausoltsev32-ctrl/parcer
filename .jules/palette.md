## 2024-05-13 - Add labels to auth forms
**Learning:** Found a pattern where auth form inputs (login/register) rely entirely on placeholders for identification, which breaks accessibility for screen readers and creates usability issues when the input is filled.
**Action:** Always ensure form inputs have proper `<label>` elements with matching `htmlFor`/`id` attributes, even if visually relying on placeholders.
