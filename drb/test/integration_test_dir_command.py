from drb.docker import SpawnedProcessError
from unittest2 import TestCase, skipIf
from click.testing import CliRunner
import os
import sys

from drb.tempdir import TempDir
from drb.commands.dir import dir
from drb.docker import Docker

REFERENCE_IMAGE = "alanfranz/drb-epel-7-x86-64:latest"

class TestDirCommand(TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.src = TempDir.platformwise()
        self.rpm = TempDir.platformwise()

    def tearDown(self):
        self.src.delete()
        self.rpm.delete()


    def test_dir_command_fails_if_sources_unavailable_and_downloadsources_not_enabled(self):
        with open(os.path.join(self.src.path, "tmux.spec"), "wb") as f:
            f.write(TMUX_SPEC)

        self.assertRaises(SpawnedProcessError, self.runner.invoke, dir, [REFERENCE_IMAGE, self.src.path, self.rpm.path],
                          catch_exceptions=False)

    def test_dir_command_produces_binary_rpm_and_debuginfo_packages_if_valid_spec_passed_and_downloadsources_enabled(self):
        with open(os.path.join(self.src.path, "tmux.spec"), "wb") as f:
            f.write(TMUX_SPEC)

        self.runner.invoke( dir, [REFERENCE_IMAGE, self.src.path, self.rpm.path, "--download-sources"],  catch_exceptions=False)
        self.assertEquals(2, len(os.listdir(os.path.join(self.rpm.path, "x86_64"))))


    def test_dir_command_produces_signed_binary_rpm_if_signing_requested(self):
        with open(os.path.join(self.src.path, "tmux.spec"), "wb") as f:
            f.write(TMUX_SPEC)
        with open(os.path.join(self.src.path, "sign.gpg"), "wb") as f:
            f.write(SIGN_PRIV)
        with open(os.path.join(self.rpm.path, "sign.pub"), "wb") as f:
            f.write(SIGN_PUB)

        self.runner.invoke(dir, [REFERENCE_IMAGE, self.src.path, self.rpm.path, "--download-sources", "--sign-with", os.path.join(self.src.path, "sign.gpg") ],  catch_exceptions=False)

        out = Docker().rm().bindmount_dir(self.rpm.path, "/rpm").workdir("/rpm/x86_64").image(REFERENCE_IMAGE).\
            cmd_and_args("/bin/bash", "-c", "rpm --import ../sign.pub && rpm -K *.rpm").run()
        self.assertTrue("pgp" in out)
        self.assertTrue("OK" in out)

    @skipIf(sys.platform == "darwin", "Has no effect on OSX/Kitematic/boot2docker")
    def test_created_binaries_have_proper_ownership(self):
        with open(os.path.join(self.src.path, "tmux.spec"), "wb") as f:
            f.write(TMUX_SPEC)

        self.runner.invoke(dir, [REFERENCE_IMAGE, self.src.path, self.rpm.path, "--download-sources",
                                 "--target-ownership", "{0}:{1}".format(os.getuid(), 1234)],
                           catch_exceptions=False)

        basedir = os.path.join(self.rpm.path, "x86_64")
        for filename in os.listdir(basedir):
            sr = os.stat(os.path.join(basedir, filename))
            self.assertEquals(os.getuid(), sr.st_uid)
            self.assertEquals(1234, sr.st_gid)

TMUX_SPEC = """
Name:           tmux
Version:        1.6
Release:        3%{?dist}
Summary:        A terminal multiplexer

Group:          Applications/System
# Most of the source is ISC licensed; some of the files in compat/ are 2 and
# 3 clause BSD licensed.
License:        ISC and BSD
URL:            http://sourceforge.net/projects/tmux
Source0:        http://pkgs.fedoraproject.org/repo/pkgs/tmux/tmux-1.6.tar.gz/3e37db24aa596bf108a0442a81c845b3/tmux-1.6.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  ncurses-devel
BuildRequires:  libevent-devel

%description
tmux is a "terminal multiplexer."  It enables a number of terminals (or
windows) to be accessed and controlled from a single terminal.  tmux is
intended to be a simple, modern, BSD-licensed alternative to programs such
as GNU Screen.

%prep
%setup -q

%build
%configure
make %{?_smp_mflags} LDFLAGS="%{optflags}"

%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot} INSTALLBIN="install -p -m 755" INSTALLMAN="install -p -m 644"

%clean
rm -rf %{buildroot}

%post
if [ ! -f %{_sysconfdir}/shells ] ; then
    echo "%{_bindir}/tmux" > %{_sysconfdir}/shells
else
    grep -q "^%{_bindir}/tmux$" %{_sysconfdir}/shells || echo "%{_bindir}/tmux" >> %{_sysconfdir}/shells
fi

%postun
if [ $1 -eq 0 ] && [ -f %{_sysconfdir}/shells ]; then
    sed -i '\!^%{_bindir}/tmux$!d' %{_sysconfdir}/shells
fi

%files
%defattr(-,root,root,-)
%doc CHANGES FAQ NOTES TODO examples/
%{_bindir}/tmux
%{_mandir}/man1/tmux.1.*

%changelog
* Fri Aug 09 2013 Steven Roberts <strobert@strobe.net> - 1.6-3
- Building for el6
- Remove tmux from the shells file upon package removal (RH bug #972633)
"""

SIGN_PUB = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1

mI0EVJ/XBgEEAOGka0Qsia3La0uSnduWfbp9/s08RHOjXNyHPayeBmOMPGidlqD3
qaADhQiOHHufmyC0EwDgghVGKBz/V6E6JrI10Va7iA/p5PNrSfbNiRBjM+oF+z0T
cU5tkOZcwQAGW4z64vYiVHlAgly4t6BD7s/OIoQygkH3GTsB1xR3UodrABEBAAG0
G215dXNlciA8bXl1c2VyQGV4YW1wbGUuY29tPoi+BBMBAgAoBQJUn9cGAhsDBQkB
4TOABgsJCAcDAgYVCAIJCgsEFgIDAQIeAQIXgAAKCRCpvP7x+6fJu+gYA/9Jm2XJ
00JgvDz2Qf7Q9JiussX5SIApgCT3A7ThHGcFg6/1bc788RIkylDuquraLgGkk1e9
SW6RhwZsu/6tSI6HJ6uVJ1sjLKoWHoJt592GQ+H2mD1OpVeYYlTybyAmTZHmhTz0
9ZDdjKMRF73f410W/20JKAktHCPomgEmsSshAg==
=ErQ2
-----END PGP PUBLIC KEY BLOCK-----
"""

SIGN_PRIV = """-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1

lQHYBFSf1wYBBADhpGtELImty2tLkp3bln26ff7NPERzo1zchz2sngZjjDxonZag
96mgA4UIjhx7n5sgtBMA4IIVRigc/1ehOiayNdFWu4gP6eTza0n2zYkQYzPqBfs9
E3FObZDmXMEABluM+uL2IlR5QIJcuLegQ+7PziKEMoJB9xk7AdcUd1KHawARAQAB
AAP7BSGqitY5CHwVGrtOubz/a0cM1kJTnemgeALfXA0v97kG3z4yzlTqaezBbHo9
v98go09VFHK9fgfLIppCSFlhNLkZ8LGN/ln9RvnwjwxaqScARG5eX/sdSyFEccZ6
yCw2a7YKWRMrneDnJ1359EXmHL45Ph6dyD2BuwzLk9Nri1kCAOUB1UzCA3DPr0XH
HiXE9FhG5KymH1adjeDXIPKx6UNT91QnwvrrqIGIMs2zBH3iMB1D3UtIl4/9wAnS
iS2f6EcCAPw9DUK7wlLRuGSBU7nZ4q7Wiz04pEQz32tzyGV5DXaK2VH371diWoh5
S5w4zliej5XuE4GIucNAMOXZsWtsHb0CAJ0PpIMdve4mcBShrqJCnHU5z8jCFgAp
xReBPWmBK3UyrgFl1go2T6U97XaywgzwZExboI5APKB7BkRmyOsk6dqeCrQbbXl1
c2VyIDxteXVzZXJAZXhhbXBsZS5jb20+iL4EEwECACgFAlSf1wYCGwMFCQHhM4AG
CwkIBwMCBhUIAgkKCwQWAgMBAh4BAheAAAoJEKm8/vH7p8m76BgD/0mbZcnTQmC8
PPZB/tD0mK6yxflIgCmAJPcDtOEcZwWDr/VtzvzxEiTKUO6q6touAaSTV71JbpGH
Bmy7/q1Ijocnq5UnWyMsqhYegm3n3YZD4faYPU6lV5hiVPJvICZNkeaFPPT1kN2M
oxEXvd/jXRb/bQkoCS0cI+iaASaxKyEC
=h8fb
-----END PGP PRIVATE KEY BLOCK-----"""