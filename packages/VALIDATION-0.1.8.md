# nex-editg 0.1.8 build notes

- Focused checks passed: stable colors on open tabs after Preferences changes; latest defaults on new tabs; individual/shared overrides and resets; window isolation; cancellation; on-disk session/workspace restoration; no default color duplication in document records.
- Existing tab palette check passed: legacy single-color migration, independent active/inactive custom colors, complete compact palettes, Cancel/Select, restart and workspace restoration.
- Fedora 44 RPM built with the existing script and installed on Scopuli. Installed source matched the checkout; focused default/shared checks passed against installed libraries, and the installed launcher rendered an isolated offscreen preview successfully.
- Ubuntu 26.04 DEB built with the existing script in the existing Ubuntu 26.04.1 container. No Ubuntu runtime or broad regression suite was run, per the request to keep validation minimal.
- Previous packages and source archives are retained; SHA256SUMS includes all three new release artifacts. Updater scripts are unchanged.
