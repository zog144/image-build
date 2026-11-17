# Nonresident Certbot — Python 3.12 offline dependencies (2026-11-17)

## Actual native predecessor

The original Amazon Linux 2023 nonresident Host already has root-owned
zog 0.1.1.dev20261117 installed under /usr/lib/python3.12/site-packages.
The November 17 retained report verifies all 509 installed aggregate RECORD
members and 16 /usr/bin launchers. Native installed aggregate RECORD SHA-256:

8a4428184d096a1f24e68b394b6dcd26a23cf345fe59d7e74ce18c57493e6d30

There is no need to rebuild, reinstall, rewrite, upgrade or move this
verified zog package. The original report showed all ten direct dependencies
missing and exactly two imports failing from missing dbus_next:
zog.root_control.daemon and zog.root_control.systemd.

## Source-owned offline dependency closure

The ten exact aggregate Requires-Dist constraints are retained in
project/host/nonresident-certbot-python312-dependencies.in.
The separately reviewed, **fully pinned direct and transitive** selection
is in project/host/nonresident-certbot-python312-dependencies.lock.
There are 24 actual wheels, each with one fixed version and SHA-256 hash.

tools/verify_nonresident_certbot_dependency_wheelhouse.py verifies the
wheelhouse without installation. It rejects nonwheel/duplicate packages,
missing direct dependencies, changes from the source lock, and packages
attempting to replace installed zog modules. The existing aggregate wheel
is selected only by its original SHA-256:

bf8560e3ee228dc6390f708bb9282472bbc7e14b154b5841c7ba912901b204c8

GitHub CI downloads only prebuilt manylinux2014_x86_64/Python 3.12
compatible wheels from PyPI, checks every hash against the source lock,
installs the 24 dependencies fully offline in a disposable Python 3.12
environment, separately installs the unchanged original zog wheel,
runs pip check, and imports the exact 15 modules from the native report.
The source has no PyPI release, compiler-user creation, Host mutation,
station assignment or issuer activation side effect.

## image-build Work connection — native dependency-only operation

1. Fetch the reviewed wheelhouse and exact committed lock from the passing
   Actions run. Validate all 24 wheel SHA-256 identities and ensure that
   the input does not contain any zog wheel. If the artifact expires,
   reproduce exactly the committed lock and verify each new downloaded
   wheel byte-for-byte; do not select new dependency versions.
2. Reopen the SAME existing nonresident Host and confirm /usr/bin/python3.12
   is CPython 3.12, site-packages path is
   /usr/lib/python3.12/site-packages, and the existing root-owned zog
   RECORD SHA remains the exact native digest above. Retain evidence
   for the original 16 root-owned executable launchers and their
   #!/usr/bin/python3.12 shebangs.
3. Inspect whether any of the 24 direct/transitive distributions already
   exist on the real Host. The previous report proves the ten direct
   distributions were absent, but does not prove all fourteen transitives
   were absent. If an existing version differs, or a file collision is
   possible, HOLD and reconcile; never blindly uninstall or upgrade it.
4. Only on an explicitly authorized native installation operation, use
   the complete verified offline wheelhouse with the following command
   (replace the two /PATH/TO/REVIEWED prefixes with the saved inputs):

   /usr/bin/python3.12 -m pip install --no-index \
     --find-links /PATH/TO/REVIEWED/wheelhouse --require-hashes \
     --no-deps --no-cache-dir --no-compile --prefix /usr \
     -r /PATH/TO/REVIEWED/nonresident-certbot-python312-dependencies.lock

   The committed lock already names ALL transitive packages, so --no-deps
   avoids selection drift. Do not pass zog to pip; no --upgrade,
   Python 3.15, remote network, alternate user or pyc generation.
5. Independently verify installed versions and actual root-owned RECORD
   bytes of all 24 distributions under the selected interpreter,
   then use pip check and import all fifteen of the original issuer-critical
   modules under Python 3.12 with -I -B and no PYTHONPATH/PYTHONHOME.
   Confirm all 15/15 imports resolve under the selected site-packages.
   Reopen the original installed zog RECORD and 16 launchers again and
   require their exact preinstallation identities unchanged.
6. Retain an original-Host-scoped nonsecret operation receipt with lock
   SHA-256, source run/artifact, wheel hashes, installed dependency
   versions and RECORD digests, root-owned origins, Python binary,
   pre/post zog RECORD identity, pip check and 15-module import evidence.
   Keep the prior failed/superseded installation attempts as they were.

## host-install Work connection follows

After native dependency installation and import verification, host-install
Work may invoke its selected read-only root-owned attestation:

    env -u PYTHONPATH -u PYTHONHOME /usr/bin/python3.12 -I \
      -m zog.host_install certify-manage-controller-attest-installed \
      --python-executable /usr/bin/python3.12

A successful import or pip check does not itself establish issuer authority.
The original signed station DNS-01 assignment, protected credential delivery,
old-attempt reconciliation, selected preparation/inspection and certificate
issuance remain independent. Resident Zog boot is not a prerequisite.

STATUS: Exact source hash lock + real disposable offline imports PASS.
Original nonresident Host dependency installation NOT RUN in Regular.
