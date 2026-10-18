#!/bin/bash
# host-deploy job: host preparation and local behavior tests only.
set -euo pipefail
if [[ "${ZOG_AUTHORIZED_DISPOSABLE_HOST:-}" != "1" ]]; then
  echo "Refusing host mutation without explicit disposable-host authorization" >&2
  exit 2
fi
cd "$(dirname "$0")/.."
mkdir -p evidence
python3 -m zog.image_build.developer.host > evidence/host-plan.json
python3 -m zog.image_build.developer.host --install > evidence/host-install.log 2>&1
dnf -y install glibc-static python3.11 python3.11-pip >> evidence/host-install.log 2>&1
python3.11 -m venv /var/tmp/image-build-test-environment
/var/tmp/image-build-test-environment/bin/pip install pytest > evidence/python-install.log 2>&1
/var/tmp/image-build-test-environment/bin/python -m pytest -q --junitxml=evidence/tests.xml | tee evidence/tests.log
printf '%s\n' '{"systemd_build_execution":"blocked_pending_box_control_build_job_api"}' > evidence/integration-status.json
