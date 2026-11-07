#!/usr/bin/env python3
"""Run on Fedora 44/45 for RPM or Ubuntu 26.04 for DEB."""
import argparse, pathlib, shutil, subprocess, sys
p = argparse.ArgumentParser()
p.add_argument('format', choices=['rpm', 'deb'])
a = p.parse_args()
root = pathlib.Path(__file__).resolve().parents[1]
v = (root/'VERSION').read_text().strip()
fedora = ''
if a.format == 'rpm':
    import platform
    os_release = platform.freedesktop_os_release()
    fedora = os_release.get('VERSION_ID', '')
    expected_python = {'44': (3, 14), '45': (3, 15)}
    if os_release.get('ID') != 'fedora' or fedora not in expected_python or sys.version_info[:2] != expected_python[fedora]:
        p.error('RPM builds require Fedora 44/Python 3.14 or Fedora 45/Python 3.15')
    if platform.machine() != 'x86_64':
        p.error('RPM builds require x86_64')
    python_minor = expected_python[fedora][1]
b = root/'build/packages'/a.format
if b.exists(): shutil.rmtree(b)
stage = b/'stage'
app = stage/'opt/nex-editg'
app.mkdir(parents=True)
def run(*args): subprocess.run(args, check=True)
run(sys.executable, '-m', 'pip', 'install', '--no-compile', '--target', str(app/'lib'), '-r', str(root/'requirements.txt'))
for name in ['editor.py', 'enhancements.py', 'git_browser.py', 'VERSION', 'CHANGELOG.md', 'requirements.txt']:
    shutil.copy2(root/name, app/name)
for name in ['icons', 'Examples']:
    shutil.copytree(root/name, app/name)
for src, dst in [('packaging/nex-editg','usr/bin/nex-editg'), ('packaging/nex-editg.desktop','usr/share/applications/com.greenfinch628.nex-editg.desktop'), ('icons/app-ned.svg','usr/share/icons/hicolor/scalable/apps/com.greenfinch628.nex-editg.svg')]:
    dest=stage/dst; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(root/src,dest)
out=root/'packages'/(f'fedora-{fedora}' if a.format=='rpm' else 'ubuntu-26.04')
out.mkdir(parents=True,exist_ok=True)
if a.format=='deb':
    (stage/'DEBIAN').mkdir()
    (stage/'DEBIAN/control').write_text(f"""Package: nex-editg
Version: {v}-1ubuntu26.04.1
Architecture: amd64
Maintainer: Bob Czys <greenfinch628@users.noreply.github.com>
Depends: python3 (>= 3.14), python3 (<< 3.15), libenchant-2-2, hunspell-en-us, libgl1, libegl1, libopengl0, libdbus-1-3, libfontconfig1, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0, libxcb-xkb1, libxcb-randr0, libxcb-sync1, libxcb-xfixes0, libsm6, libice6, libglib2.0-0t64
Section: editors
Priority: optional
Description: nex-editg text editor with workspace sessions and recovery
 Private pinned Qt and QScintilla dependencies are included under /opt/nex-editg.
""")
    run('dpkg-deb','--root-owner-group','-Zzstd','--threads-max=2','--build',str(stage),str(out/f'nex-editg_{v}-1ubuntu26.04.1_amd64.deb'))
else:
    spec=b/'nex-editg.spec'
    spec.write_text(f"""%global debug_package %{{nil}}
%global __os_install_post %{{nil}}
Name: nex-editg
Version: {v}
Release: 1%{{?dist}}
Summary: Text editor with workspace sessions and recovery
License: LicenseRef-No-License
URL: https://github.com/greenfinch628/nex-editg
AutoReqProv: no
Requires: python3 >= 3.{python_minor}, python3 < 3.{python_minor + 1}, enchant2, hunspell-en-US
Requires: libglvnd-glx, libglvnd-egl, libglvnd-opengl, dbus-libs, fontconfig, libxkbcommon, libxkbcommon-x11, xcb-util-cursor, xcb-util-wm, xcb-util-image, xcb-util-keysyms, xcb-util-renderutil, libxcb, libSM, libICE, glib2
%description
Text editor with private pinned Qt and QScintilla dependencies.
The application source has no declared distribution license.
Dependency license notices are retained in the private library directory.
%prep
%build
%install
mkdir -p %{{buildroot}}
cp -a {stage.resolve()}/. %{{buildroot}}/
%files
/opt/nex-editg
/usr/bin/nex-editg
/usr/share/applications/com.greenfinch628.nex-editg.desktop
/usr/share/icons/hicolor/scalable/apps/com.greenfinch628.nex-editg.svg
""")
    run('rpmbuild','-bb','--define',f'_topdir {b.resolve()}/rpmbuild',str(spec))
    for f in (b/'rpmbuild/RPMS').rglob('*.rpm'): shutil.copy2(f,out/f.name)
print(out)
