# nex-editg - 0.1.2

- 2026-10-29T13:53:34Z — Fixed: Always offer Save, Discard, and Cancel when closing a changed named or unnamed tab; preserve app-close preferences and unsaved session restoration.

- 2026-10-17T14:11:15Z — Added: Version 0.1.2 RPM, DEB, and source packaging for strict insertion-position spelling suggestions. Corrected the older Scopuli desktop shortcut to use the packaged launcher. Work assisted by OpenAI Codex.
- 2026-10-17T13:59:57Z — Changed: Installed the tested spelling-click refinement on Scopuli, Rocinante, Karakum, and Narlikar; all 185 mouse-click regression checks passed against each installed copy.
- 2026-10-17T13:51:38Z — Fixed: Open spelling suggestions only when the cursor insertion position is strictly inside a misspelled word; clicks at either word boundary retain normal cursor placement.

# nex-editg - 0.1.1


- 2026-10-16T21:14:28Z — Added: Version 0.1.1 RPM and DEB packaging for the tab color chooser and spelling click updates.
- 2026-10-16T20:58:27Z — Changed: Installed the updated color chooser and spelling click behavior on Scopuli, Narlikar, Rocinante, and Karakum. Preserved existing shortcut targets and added an application-menu shortcut on Narlikar. Spelling click and startup checks passed on all four computers; editor regression checks also passed.
- 2026-10-16T20:50:37Z — Fixed: Show spelling suggestions only when clicking a character inside a misspelled word, including its first and last letters, rather than whitespace immediately before or after it. Added boundary and Unicode click regression tests.
- 2026-10-16T18:45:27Z — Changed: Matched the tab color chooser to the Ptyxis-tc appearance with nine color columns, an extra lighter top row, rounded swatches, selection checkmarks, top Cancel/Select controls, and custom colors. Set the background to #e8e8e8 with dark labels for readability.

# nex-editg - 0.1.0

- 2026-10-15T22:26:23Z — Changed: Clarified as-is availability, absence of technical support, and discretionary consideration of bug reports and enhancements without implementation commitments.
