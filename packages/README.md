# nex-editg 0.1.10 packages

Unsigned local builds for Fedora 44 x86_64 and Ubuntu 26.04 amd64.

    sudo dnf install ./fedora-44/nex-editg-0.1.10-1.fc44.x86_64.rpm
    sudo apt install ./ubuntu-26.04/nex-editg_0.1.10-1ubuntu26.04.1_amd64.deb

Use the command for your OS from this directory. Launch with `nex-editg` or
the application menu. Python 3.14 is required. The private Qt dependencies
are included; dnf/apt resolves the native libraries. Existing recovery data
and settings are retained. Remove an older per-user source launcher with the
same display name if you prefer to see only the packaged launcher.

Source and build recipes: source/nex-editg-0.1.10-source.tar.gz.
Verify with `sha256sum -c SHA256SUMS`. See ../packaging/README.md for rebuilds.

Validation results: [VALIDATION-0.1.10.md](VALIDATION-0.1.10.md).

Fedora icon update: `fedora-44/nex-editg-0.1.9-1.fc44.x86_64.rpm`. Source: `source/nex-editg-0.1.9-source.tar.gz`. Version 0.1.9 uses the new application icon; tests were skipped as requested. Ubuntu packages remain at 0.1.8.

Fedora Word Wrap update: `fedora-44/nex-editg-0.1.10-1.fc44.x86_64.rpm`. Source: `source/nex-editg-0.1.10-source.tar.gz`. Per-tab wrapping is preserved with sessions. Ubuntu Word Wrap update: `ubuntu-26.04/nex-editg_0.1.10-1ubuntu26.04.1_amd64.deb`. See [VALIDATION-0.1.10.md](VALIDATION-0.1.10.md).

Fedora 45: `fedora-45/nex-editg-0.1.10-1.fc45.x86_64.rpm` is built on Scopuli
in a Fedora 45 Podman container using Python 3.15 and the existing pins.
It is signed with the Scopuli nex-editg RPM signing key; the public key is
`RPM-GPG-KEY-nex-editg`. Fingerprint:
`CEA0 2F71 230E 51CD 29E3 CB60 FF21 12A1 7CBC 7BEA`.
Import on the client with `sudo rpm --import RPM-GPG-KEY-nex-editg` before
running the updater. Installation and desktop launch were confirmed by the user on Karakum (Fedora 45).
