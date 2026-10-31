---
type: Log
title: zendesk-provider-kog — log
description: Curated chronological history of zendesk-provider-kog — notable changes and decisions, not a generated changelog.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [log, history]
timestamp: 2026-10-31T00:00:00Z
---

# Log

Curated history; release notes live in GitHub Releases.

## 2026-10-31: initial draft

- Four kinds: Ticket, Group, Organization, TicketField, trimmed from Zendesk's official OpenAPI document.
- Bodies declared unwrapped; envelope restored with request/response transforms, because the
  controller filters request bodies by top-level key only.
- `compareScope: updatable` everywhere, with narrow update bodies. Ticket triage fields,
  `comment`, tags and custom fields, and TicketField `custom_field_options`, are create-only.
- Subdomain fixed per install (`zendeskSubdomain`): server variables are not substituted by the
  controller.
