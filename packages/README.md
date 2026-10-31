# nex-editg 0.1.3 packages

Unsigned local builds for Fedora 44 x86_64 and Ubuntu 26.04 amd64.

    sudo dnf install ./fedora-44/nex-editg-0.1.3-1.fc44.x86_64.rpm
    sudo apt install ./ubuntu-26.04/nex-editg_0.1.3-1ubuntu26.04.1_amd64.deb

Use the command for your OS from this directory. Launch with `nex-editg` or
the application menu. Python 3.14 is required. The private Qt dependencies
are included; dnf/apt resolves the native libraries. Existing recovery data
and settings are retained. Remove an older per-user source launcher with the
same display name if you prefer to see only the packaged launcher.

Source and build recipes: source/nex-editg-0.1.3-source.tar.gz.
Verify with `sha256sum -c SHA256SUMS`. See ../packaging/README.md for rebuilds.

Validation results: [VALIDATION-0.1.3.md](VALIDATION-0.1.3.md).
