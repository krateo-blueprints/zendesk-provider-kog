---
type: Log
title: zendesk-provider-kog — log
description: Curated chronological history of zendesk-provider-kog — notable changes and decisions, not a generated changelog.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [log, history]
timestamp: 2026-11-01T00:00:00Z
---

# Log

Curated history; release notes live in GitHub Releases.

## 2026-11-01: minimum oasgen-provider raised to 0.46.0

- Below 0.46.0 a create Zendesk refuses latched the CR to `Ready=True` / `Available` after about two
  minutes with no `status.id`
  ([oasgen-provider#347](https://github.com/krateo-platformops/oasgen-provider/issues/347)). Seen live
  with a `Group` the account could not create (422 *"Private groups are not enabled for this
  account"*): latched on 0.44.0; on 0.46.0 it stayed `Creating` / `ReconcileError` for 6 minutes,
  never Available, no `status.id`. The full four-kind end-to-end run passes on 0.46.0.
- README, Chart.yaml, values.yaml and the docs state 0.46.0 (was 0.33.0). No runtime change: the
  chart cannot enforce the version, so `hack/assert-drift-invariants.py` (invariant 13) keeps every
  stated minimum identical.
- Also documented (2026-10-31): a Ticket's `organization_id` is honoured only when the requester
  belongs to that organization. Otherwise Zendesk files the ticket under the requester's own
  organization with a 201 and no error.

## 2026-10-31: initial draft

- Four kinds: Ticket, Group, Organization, TicketField, trimmed from Zendesk's official OpenAPI document.
- Bodies declared unwrapped; envelope restored with request/response transforms, because the
  controller filters request bodies by top-level key only.
- `compareScope: updatable` everywhere, with narrow update bodies. Ticket triage fields,
  `comment`, tags and custom fields, and TicketField `custom_field_options`, are create-only.
- Subdomain fixed per install (`zendeskSubdomain`): server variables are not substituted by the
  controller.
