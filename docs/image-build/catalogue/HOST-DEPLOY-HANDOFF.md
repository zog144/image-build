# host-deploy handoff

host-deploy owns AWS credentials, independent host allocation, source transfer,
job scheduling, cancellation, stop/start and evidence collection. Build process
isolation belongs to box-control and root-control, not host-deploy or image-build.

## Verified infrastructure

The supplied host-deploy 0.5.0 was used successfully with a new image-build
workspace in us-east-1. Its owned Amazon Linux 2023 t3.small has a 20 GiB root
disk and a 60-minute uptime timer. It is now stopped. A separate recovery bundle
contains the portable workspace checkpoint and collected job evidence, without
credentials. Restore that checkpoint rather than creating a replacement host.

The source archive required a local packaging fix to install with setuptools:

```toml
[tool.setuptools.packages.find]
include = ["host_deploy*"]
```

The original host-deploy attachment was not modified. The provided credential
CSV was privately converted to the importer's colon-delimited format, handling
its UTF-8 byte-order mark; values were not printed or transferred to EC2.

## Current reusable test job

ZIP this source tree with files at the archive root and use
`jobs/host-deploy-recipe.json`: argv `["bash", "jobs/amazon_linux_acceptance.sh"]`,
1200-second timeout, outputs `["evidence"]`, empty environment. Use a new job name
only for an intentional new execution; inspect existing jobs after lost replies.

This recipe installs Amazon Linux development/Python test prerequisites, runs
the local behavior suite, and reports the controller integration as blocked.
It does not install Docker/Podman or claim systemd build acceptance.

The native example test requires cc, ar and static libc support. Recording-runner
bootstrap tests do not verify real execution. Collect logs, XML and the integration
status. An interrupted job or missing status is never a passing result.

## Future real acceptance

After the box-control build-job interface is implemented, provision its daemon
and supported Python environment and run the tests specified in
BOX-CONTROL-BUILD-EXECUTION-REQUEST.md. Submit only small source/recipe bundles;
large compiler sources should be fetched and hash-verified on the host. S3 is
not required for the existing small SSM transfer path.

Do not delete a controller-pinned build root or retry an uncertain launch.
Lifecycle stop/cleanup and recovery must go through box-control. Stop the owned
host after jobs and evidence collection are complete.
