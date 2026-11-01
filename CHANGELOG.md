# nex-editg - 0.1.5
- 2026-11-01T12:51:12Z - Added 3-pixel white spacing between the line-number gutter and editor text. 

# nex-editg - 0.1.4

# nex-editg - 0.1.3

- 2026-10-31T21:39:12Z — Changed: Installed the About version update locally in /opt/nex-editg and updated the local source checkout.
- 2026-10-31T21:28:41Z — Added: Display the application version in About using the existing version metadata.
- 2026-10-31T15:16:42Z — Fixed: Rebuild Fedora 44 RPM and Ubuntu 26.04 DEB packages with the tab-close Save, Discard, and Cancel fix, including failed/canceled saves and unchanged app-close session recovery.

# nex-editg - 0.1.2

- 2026-10-30T00:51:33Z — Changed: Designate GitHub main as authoritative and Gitea as its backup mirror; clarify installation source and merged-branch cleanup.

- 2026-10-29T13:57:08Z — Changed: Installed the tab-close save prompt in the local nex-editg application. Verified Save, Discard, and Cancel for named and unnamed tabs, canceled and failed saves, and unchanged unsaved-session restoration after closing the app.
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
