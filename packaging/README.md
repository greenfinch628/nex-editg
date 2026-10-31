# Linux packages

Version 0.1.3 includes the tab-close Save/Discard/Cancel fix, the tab color chooser, and strict insertion-position spelling click behavior. Build RPMs on Fedora 44 x86_64
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
