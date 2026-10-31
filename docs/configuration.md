---
type: Configuration
title: zendesk-provider-kog — configuration
description: The whole config surface — the chart values resourceGroup and zendeskSubdomain, the four RestDefinition mappings (identifiers, status fields, compareScope, verbs, envelope transforms), the per-field compared / create-only / excluded decisions with reasons, every deviation from Zendesk's OpenAPI document, and the invariants hack/assert-drift-invariants.py enforces.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [krateo, values, restdefinition, oasgen-provider, zendesk]
timestamp: 2026-10-31T00:00:00Z
---

# Configuration

## Chart values

| Value | Default | Notes |
|-------|---------|-------|
| `resourceGroup` | `zendesk.krateo.io` | API group of the 4 resource CRDs and their 4 Configuration CRDs |
| `zendeskSubdomain` | `""` | **Required.** DNS label only; substituted into every asset's server URL at render time |

Resource CRs are `zendesk.krateo.io/v2` (from each asset's `info.version: v2`); Configuration CRs are
`zendesk.krateo.io/v1alpha1`.

## Per-kind mapping

| Kind | Verbs | Identifier | additionalStatusFields | Excluded spec | compareScope |
|------|-------|-----------|------------------------|---------------|--------------|
| Ticket | POST / GET / PUT / DELETE | `id` | url, created_at, updated_at, observed | ticket_id | updatable |
| Group | POST / GET / PUT / DELETE | `id` | url, default, deleted, created_at, updated_at | group_id | updatable |
| Organization | POST / GET / PUT / DELETE | `id` | url, created_at, updated_at | organization_id | updatable |
| TicketField | POST / GET / PUT / DELETE | `id` | url, key, created_at, updated_at | ticket_field_id | updatable |

Item paths take the id from `status.id` via `fieldMapping` (`inPath` ← `status.id`). Create and
update carry `requestTransform: {<wrapper>: .}`, while create, get and update carry the identical
unwrap `responseTransform` ([overview](./overview.md#the-envelope)). Group's get also declares
`notFoundBody: ((.group // .) | .deleted) == true`, and Ticket's get declares a defensive
`status == "deleted"` one.

## Compared, create-only, excluded

**Compared** fields are in the update body, so they are reconciled. **Create-only** fields are in the
create body only: sent once, never compared, never re-sent. **Excluded** fields are not modelled.

### Ticket

| Field | Decision | Why |
|-------|----------|-----|
| subject | compared | owned by the CR; read back verbatim |
| external_id | compared | link to the local record; read back verbatim |
| comment | create-only | write-only (response has `description` instead); on update Zendesk **adds** a new comment |
| status | create-only | agent/automation-owned; solved→closed is automatic and a closed ticket rejects updates (422) |
| priority, type, group_id, assignee_id | create-only | initial triage; comparing would revert agents' changes |
| organization_id, requester, requester_id, submitter_id | create-only | identity of the request; `requester` is write-only |
| tags | create-only | triggers and drop-down fields add tags; update replaces the set |
| custom_fields | create-only | request `[{id,value}]` for some fields; response lists every field on the form |
| ticket_form_id, brand_id | create-only | set once |
| description, raw_subject | excluded | ignored on update / a second source of truth for subject |
| (timestamps, id, url) | status only | server-assigned |

### Group

| Field | Decision | Why |
|-------|----------|-----|
| name, description | compared | read back verbatim |
| is_public | create-only | a private group cannot be made public |
| default | excluded | account-wide singleton; CRs would fight over it |

### Organization

| Field | Decision | Why |
|-------|----------|-----|
| name | compared | pattern forbids leading/trailing whitespace and `\|`, which Zendesk trims/rejects |
| details, notes, group_id | compared | read back verbatim (notes need an admin token, or Zendesk ignores other fields with a 200) |
| external_id | compared | pattern forbids upper-case: Zendesk compares it case-insensitively |
| domain_names, tags | create-only | destructive replace on update, normalised |
| organization_fields | create-only | merge semantics, values typed by field definition |
| ticket_restriction, shared_comments | create-only | coupled to each other and to account features |
| shared_tickets | excluded | deprecated in favour of ticket_restriction |

### TicketField

| Field | Decision | Why |
|-------|----------|-----|
| title, description, agent_description, active, required | compared | read back verbatim (no `{{dc.*}}` placeholders: they come back rendered) |
| type | create-only | immutable after creation |
| custom_field_options | create-only | update is **replace-by-id**: options without ids are re-created, omitted ones removed with their values on tickets |
| title_in_portal, visible/editable/required_in_portal | create-only | interdependent; coercion undocumented |
| position, tag, regexp_for_validation | create-only | re-laid-out by forms / type-specific |
| raw_title, sub_type_id | excluded | dynamic-content source / system fields only |

## Deviations from Zendesk's OpenAPI document

Each one is commented where it is made in `chart/assets/<kind>.yaml`. In summary:

- Request and response bodies are declared **unwrapped**; the RestDefinitions restore the envelope.
- `info.version` is `v2` (official `2.0.0` would become CRD version `v2-0-0`).
- The `subdomain` server-variable default is `your-subdomain` (official `example`).
- Security schemes are trimmed to `basicAuth` (official also has bearer and OAuth2).
- Path ids are declared `string` (official int64), the form a path parameter is substituted in.
- Query parameters (sideloads, payload options) are dropped, because they would become spec fields.
- `oneOf` unions are trimmed to one branch: Ticket `requester` (object), `tags` (array),
  `custom_fields[]` (`{id, value: string}`), `brand_id` (integer); Organization `external_id`
  (string) and `organization_fields` values (string).
- Added constraints: Ticket `comment` required; TicketField `type` required with a trimmed enum
  (no lookup/credit-card types); patterns on Organization `name` / `external_id` and on option
  `value`.
- Ticket's response schema gains `observed`, which the response transform produces.

## Invariants (`hack/assert-drift-invariants.py`, run in CI)

1. Every RestDefinition declares exactly `compareScope: updatable`.
2. Each update body is **exactly** the compared set above.
3. Every create-only field is absent from the update body and present in the create body.
4. Excluded fields are in neither body.
5. No request or GET-response schema declares the envelope key (e.g. `ticket`).
6. Create/update carry `{<wrapper>: .}`; get/delete carry no requestTransform; create/get/update carry
   the identical unwrap.
7. No identifier or status field shares a name with a request-body property.
8. Every verb's path and method exist in its asset, and mapped path parameters exist on the path.
9. `servers[0].url` is the official template, present exactly once.
10. Security is exactly HTTP basic.
11. Group's get declares a `notFoundBody` on `.deleted`.
