# Linux packages

Version 0.1.10 adds per-tab Word Wrap with session restoration. Build RPMs on Fedora 44 x86_64
and DEBs on Ubuntu 26.04 amd64, using Python 3.14 and pip:

    python3 packaging/build.py rpm
    python3 packaging/build.py deb

Run only the command matching the build environment. RPM requires rpm-build;
DEB requires dpkg-deb. Network access to PyPI is needed to resolve the pinned
requirements. Packages include private Qt/PyQt/QScintilla/pyenchant libraries
and their license notices under /opt/nex-editg/lib. Native system libraries
are declared as package dependencies. The application has no declared source
license; this packaging does not assign one. Review licensing before wider
redistribution. Install with dnf install ./package.rpm or apt install ./package.deb.
These are unsigned local builds. Ubuntu 24.04 and other Python minor versions
are unsupported. The shared application data path is preserved.

Fedora 45 x86_64 uses Python 3.15 with the same dependency pins. On Scopuli,
run `~/bin/Applications-scripts/createNexEditgRpm.sh 45` to build in Podman
without upgrading the Fedora 44 host. Output is in `packages/fedora-45`.
