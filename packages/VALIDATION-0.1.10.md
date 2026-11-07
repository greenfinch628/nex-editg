# nex-editg 0.1.10 validation

- Per-tab Word Wrap manually tested by the user and reported working correctly.
- Fedora 44 RPM built and installed on Scopuli by the user.
- Installed version is 0.1.10; installed editor.py and enhancements.py match the release source. RPM file verification passed.
- Python syntax check passed for the Word Wrap implementation. No comprehensive test suite or additional package build was run.
- Generated build output, prototype virtual environment, and Python cache removed after installation. Source development tools and previous release packages retained.
- Ubuntu 26.04 amd64 DEB built by the user. Package metadata reports 0.1.10-1ubuntu26.04.1; bundled VERSION, editor.py, enhancements.py, and git_browser.py match the release source. Ubuntu installation and runtime testing were not performed in this session.

## Fedora 45 RPM — 2026-11-07

Built on Scopuli (host remains Fedora 44), in registry.fedoraproject.org/fedora:45
with Python 3.15.0 and unchanged requirements.txt pins.
Artifact: fedora-45/nex-editg-0.1.10-1.fc45.x86_64.rpm.
Verified release/architecture, python3 >= 3.15 and python3 < 3.16 requirements,
and OpenPGP RSA/SHA512 signature plus header/payload SHA256 digests (all OK).
Signing fingerprint: CEA02F71230E51CD29E3CB60FF2112A17CBC7BEA.
Re-running createNexEditgRpm.sh 45 skips the existing RPM. Shell syntax checks
and simulated Fedora 44/45 missing-package checks passed before any download.
Fedora 44 RPMs and Ubuntu DEBs were preserved. The user confirmed successful
installation and desktop launch on Karakum (Fedora 45) and approved completion.
Rocinante testing remains for its Fedora 45 upgrade.
