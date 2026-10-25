# certify-manage application definitions

This directory contains maintained source definitions for immutable `certify-manage`
application software.

## `cloudflare-dns-01.json`

The Cloudflare definition is a complete **runtime-lock candidate** for Certbot 5.8.0
with the `dns-cloudflare` authenticator. It contains the accepted HTTP-01 core
closure plus the complete Cloudflare runtime delta:

- `certbot-dns-cloudflare` 5.8.0;
- `cloudflare` 5.6.0;
- AnyIO / HTTPX / HTTPCore / h11;
- Pydantic / pydantic-core / annotated-types;
- sniffio and typing-inspection.

The definition also carries the exact source hashes, immutable notice-copy plan,
accepted CPython/rootfs compatibility descriptor, and the Cloudflare-specific
offline build-input delta. It never contains a Cloudflare token or ACME mutable
state.

`publication_authorized` is deliberately **false**. The historical DNS source
review left the pydantic-core Rust closure pending per-component grant/notice and
selected native-output review. The definition is suitable for completing that
review and for a source-bound Work build, but its existence is not native
acceptance.

The already accepted `http-01` artifact/view is separate and must not be mutated
or relabeled as this profile.
