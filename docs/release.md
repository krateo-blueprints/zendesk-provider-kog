---
type: Runbook
title: zendesk-provider-kog — release
description: How a release ships — one plain-semver tag drives the release-oci workflow, which stamps CHART_VERSION, pushes the chart to GHCR and publishes the same archive to the Marketplace's operators index. The chart is the only artifact this repo publishes.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [release, oci, ghcr, chart]
timestamp: 2026-11-07T00:00:00Z
---

# Release

One plain-semver tag (`X.Y.Z`, **no** `v` prefix) releases everything. The tag push runs
`.github/workflows/release-oci.yaml`, which publishes the chart twice, with the same bytes, as the
organisation's publishing standard requires
([krateo-blueprints/charts PUBLISHING.md](https://github.com/krateo-blueprints/charts/blob/main/PUBLISHING.md)):

1. refuses to start unless the tagged commit has a successful `lint` run and the org secret
   `CHARTS_PUBLISH_TOKEN` is set, so nothing reaches GHCR that cannot also reach the Marketplace;
2. substitutes `CHART_VERSION` in `chart/Chart.yaml` with the tag (a manual run may only re-release
   a tag, never set another version);
3. `helm package`s `chart/` and checks it is operators content: the standard puts a chart in the
   `blueprints` channel only when it has a `values.schema.json` **and** a `CompositionDefinition`,
   and this chart has no `CompositionDefinition`;
4. pushes it to `oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog`;
5. publishes the same archive to the Marketplace's `operators` index
   (`https://krateo-blueprints.github.io/charts/operators`) through the organisation's publisher
   (`krateo-blueprints/charts/.github/workflows/publish-chart.yaml@1`). The portal Marketplace
   installs from that index, not from GHCR; the publisher succeeds only once the served index lists
   the version and `helm pull --repo` installs it anonymously.

`release-notes.yaml` generates the release notes on the same tag.

There is no image and nothing to co-version. Bump `appVersion` in `chart/Chart.yaml` when the
OpenAPI assets or mappings change.

Before tagging, CI (`lint.yaml`) must be green: docs standard, drift invariants, and `helm lint` /
`helm template` with `CHART_VERSION` stamped to `0.0.0-ci`.
