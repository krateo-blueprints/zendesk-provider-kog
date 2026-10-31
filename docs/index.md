---
type: Component
title: zendesk-provider-kog — index
description: The map of the zendesk-provider-kog doc bundle — a Krateo KOG provider that exposes the Zendesk Support API's ticketing surface (Ticket, Group, Organization, TicketField) as zendesk.krateo.io Kubernetes kinds via oasgen-provider.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [krateo, kog, oasgen-provider, zendesk, ticketing]
timestamp: 2026-10-31T00:00:00Z
---

# zendesk-provider-kog

zendesk-provider-kog is a Krateo **KOG** (Krateo OpenAPI Generation) provider: a Helm chart of
`RestDefinition`s plus trimmed OpenAPI documents that `oasgen-provider` turns into CRDs and a
`rest-dynamic-controller` per kind. It covers the four Zendesk resources a platform needs to run
ticketing for its tenants:

| Kind | Role |
|------|------|
| `Organization` | one per tenant, keyed by `external_id` |
| `Group` | the routing target for a category of tickets |
| `TicketField` | the category taxonomy (a drop-down custom field) |
| `Ticket` | a ticket filed by the platform |

Four facts hold across the set:

- **All four are native**: every verb calls `https://<subdomain>.zendesk.com` directly. The chart
  ships no runtime component ([overview](./overview.md)).
- **Reconciliation is deliberately narrow.** Each kind compares only the fields its update body
  carries (`compareScope: updatable`), and those are exactly the fields that read back as written
  and that the CR owns after creation. Everything else is create-only ([configuration](./configuration.md)).
- **One install = one Zendesk account.** The subdomain is a chart value because the controller does
  not substitute OpenAPI server variables ([configuration](./configuration.md)).
- **oasgen-provider ≥ 0.33.0 is required** ([usage](./usage.md)).

## Bundle

- [overview](./overview.md): how it works, and how Zendesk's body envelope is handled.
- [usage](./usage.md): install, credentials, driving the kinds, verifying.
- [configuration](./configuration.md): values, per-kind mappings, compared vs create-only, invariants.
- [api](./api.md): the generated CRDs and the CompositionDefinition.
- [examples](./examples.md): runnable examples.
- [release](./release.md): how a release ships.
- [log](./log.md): curated history.
