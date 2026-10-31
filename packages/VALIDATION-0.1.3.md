# nex-editg 0.1.3 validation

Built October 31, 2026 from GitHub main at 8f31c94 plus the 0.1.3 version and release documentation update. Includes the October 29 tab-close Save/Discard/Cancel fix.

- RPM built on Fedora 44 x86_64 with Python 3.14; integrity check and upgrade dry run passed.
- All nine check_*.py regression scripts passed against the Fedora staged application and bundled libraries. Extracted RPM files match that tested staging tree byte for byte.
- DEB built and installed in an isolated Ubuntu 26.04 amd64 container using Python 3.14. All nine regression scripts passed against the installed application and bundled libraries. Git was added as a test prerequisite.
- Both packaged applications match the release source, including VERSION and CHANGELOG.md.
- Checks cover named/unnamed tab Save, Discard, Cancel, failed/canceled saves, app-close session recovery, 185 spelling clicks, launch forwarding, sidebar actions, rename, and welcome behavior.
- Matching source archive and SHA256SUMS supplied; previous package versions retained.
- GUI checks used Qt offscreen mode. No interactive GNOME/Wayland check was performed for this packaging-only release.
- The host nex-editg installation was not upgraded by this packaging task.
