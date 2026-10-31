---
type: Runbook
title: zendesk-provider-kog — release
description: How a release ships — one plain-semver tag drives the canonical release-oci workflow, which stamps CHART_VERSION and packages the chart to GHCR. The chart is the only artifact this repo publishes.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [release, oci, ghcr, chart]
timestamp: 2026-10-31T00:00:00Z
---

# Release

One plain-semver tag (`X.Y.Z`, **no** `v` prefix) releases everything. The tag push runs
`.github/workflows/release-oci.yaml` (the canonical org workflow, byte-identical across repos), which:

1. substitutes `CHART_VERSION` in `chart/Chart.yaml` with the tag;
2. `helm package`s `chart/`;
3. pushes it to `oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog`.

`release-notes.yaml` generates the release notes on the same tag.

There is no image and nothing to co-version. Bump `appVersion` in `chart/Chart.yaml` when the
OpenAPI assets or mappings change.

Before tagging, CI (`lint.yaml`) must be green: docs standard, drift invariants, and `helm lint` /
`helm template` with `CHART_VERSION` stamped to `0.0.0-ci`.
