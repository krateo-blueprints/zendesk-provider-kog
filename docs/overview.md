---
type: Architecture
title: zendesk-provider-kog — overview
description: What the chart ships and how it works — four RestDefinitions plus trimmed Zendesk OpenAPI documents that oasgen-provider turns into zendesk.krateo.io CRDs and a controller per kind; how Zendesk's wrapped bodies are handled with request/response transforms; why drift is scoped to the update body; and why the subdomain is fixed per install.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [krateo, kog, oasgen-provider, rest-dynamic-controller, zendesk]
timestamp: 2026-10-31T00:00:00Z
---

# Overview

## What the chart renders

Per kind, one `ConfigMap` holding `chart/assets/<kind>.yaml` (a trimmed copy of Zendesk's official
OpenAPI document, with its server URL resolved) and one `RestDefinition`
(`ogen.krateo.io/v1alpha1`) pointing at it with `oasPath: configmap://…`. Nothing else: no
Deployment, no Service, no image.

`oasgen-provider` reads each RestDefinition and generates:

- a resource CRD (`Ticket`, `Group`, `Organization`, `TicketField`) whose **spec** comes from the
  create operation's request body and whose **status** comes from the identifiers and
  `additionalStatusFields` looked up in the GET response schema;
- a `<Kind>Configuration` CRD from the document's security scheme (HTTP basic);
- a `rest-dynamic-controller` Deployment that reconciles CRs of that kind against Zendesk.

## The envelope

Zendesk wraps request and response bodies in a key named after the resource
(`{"ticket": {...}}`, `{"ticket_field": {...}}`). The assets declare the **unwrapped** object, and
every RestDefinition converts at the wire:

| Verb | requestTransform | responseTransform |
|------|------------------|-------------------|
| create | `{ticket: .}` | unwrap `.ticket` |
| get | none | unwrap `.ticket` |
| update | `{ticket: .}` | unwrap `.ticket` |
| delete | **none** (would send a body on DELETE) | none |

Why the assets do not keep the official wrapper:

1. The controller filters an outgoing body to the operation's declared properties **by top-level key
   only**. With a wrapper, the update declares just `ticket`, so the whole spec object passes, and
   for Ticket that includes the write-only `comment`, which Zendesk would post as a new comment on
   every drift-triggered update.
2. Status is cleared and repopulated from the create and update responses as well as the get, so all
   three must be unwrapped or `status.id` is lost and the next observe cannot address the resource.

Ticket's response transform also builds `observed` (status, priority, type, group, assignee,
organization, requester, tags), a read-only mirror of the help-desk-owned fields under a name that
does not collide with any request field. The controller copies a status field into a request whenever
the spec omits a field of the same name, so such a collision would re-send last-observed values. For
example, a re-created ticket would be filed as `closed`.

## Drift

Every kind declares `compareScope: updatable`: the controller compares only the leaf paths the update
body declares, and only those the CR actually sets. The update bodies are chosen so that every compared
field (a) is owned by the CR after creation and (b) reads back exactly as written. The default,
`fullSpec`, would compare every echoed spec key, and Zendesk echoes nearly everything, in shapes or
with owners that make the comparison wrong.
[configuration](./configuration.md#compared-create-only-excluded) has the per-field table.

Two consequences hold for every kind:

- Removing an optional field from the CR does not clear it in Zendesk, because an absent spec field is
  not compared.
- A difference the update cannot resolve, for example an edit to a ticket that has since closed (422),
  is reported as `DriftNotConverging` after the controller's retry budget instead of being retried
  forever.

## Deletion

| Kind | Zendesk delete | After delete, GET answers | Controller |
|------|----------------|---------------------------|------------|
| Ticket | soft (Deleted Tickets, purged after 30 days) | 404 per Zendesk docs; a defensive `notFoundBody` also covers a `status: deleted` tombstone | finalizer released on 404 |
| Group | soft (`deleted: true` on the record) | possibly 200 with `deleted: true` | `notFoundBody` reads it as gone; without it the CR would hang in Deleting |
| Organization | hard | 404 | finalizer released |
| TicketField | hard (values removed from tickets) | 404 | finalizer released |

Level-based reconciliation also means that a resource deleted **in Zendesk** while its CR exists is
re-created on the next observe. For a Ticket that is a new ticket with a new id, and the first comment
is posted again.

## The server URL

`rest-dynamic-controller` uses `servers[0].url` verbatim and does not substitute OpenAPI server
variables, and Configuration CRs can only feed path/query/header/cookie parameters. The assets therefore
keep the official template `https://{subdomain}.{domain}.com`, and the ConfigMap replaces it with
`https://<zendeskSubdomain>.zendesk.com` at render time. The render fails if the value is missing or
invalid, or if the template is not found exactly once.
