# nex-editg 0.1.6 validation

- Fedora 44 x86_64 RPM built using the existing packaging script and Python 3.14. RPM digest verification passed; installed successfully on Scopuli. Installed source and version match the tested release, and RPM file verification passed.
- All ten source and Fedora staged-package regression scripts passed, including 185 spelling clicks, editing, launch forwarding, tab-close Save/Discard/Cancel, sidebar, rename, and recovery checks.
- Focused color checks cover both complete palettes, 740×275 dialog visibility, selection checkmarks, swatch clicks, independent custom colors, canceled custom chooser, transactional Cancel/Select, opposite light/dark combinations, tab switching/rendering, fresh-process restart, legacy migration, and workspace restoration. Installed Scopuli color checks passed.
- Ubuntu 26.04 amd64 DEB built using the existing packaging script in the Ubuntu builder. Installed and tested in the Ubuntu verification container with Git supplied as a test prerequisite. All ten regression scripts passed; installed source and version match the release.
- Tests used isolated state directories and Qt offscreen rendering. The chooser rendering was visually inspected; no interactive GNOME/Wayland acceptance test was performed. Existing user sessions and preferences were not modified by tests.
- RPM, DEB and source archive use distinct 0.1.6 filenames. Earlier artifacts and checksum records are retained.
