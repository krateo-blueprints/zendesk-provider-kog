---
type: API
title: zendesk-provider-kog — API
description: The CRDs this component brings into the cluster — Ticket, Group, Organization and TicketField under zendesk.krateo.io/v2 with their spec, status and verbs, the oasgen-generated <Kind>Configuration kind each one gets (HTTP basic auth from a Secret), and the CompositionDefinition the core-provider CDC derives from values.schema.json.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [krateo, crd, compositiondefinition, zendesk, oasgen-provider]
timestamp: 2026-10-31T00:00:00Z
---

# API

## Component

The chart is registered through a **CompositionDefinition** whose CRD the core-provider CDC derives
from `chart/values.schema.json`: two scalars, `resourceGroup` and `zendeskSubdomain`.

## Generated resource kinds (`zendesk.krateo.io/v2`)

| Kind | Spec (create body) | Status |
|------|--------------------|--------|
| `Ticket` | subject, comment{body, html_body, public, author_id}, requester{name, email, locale_id}, requester_id, submitter_id, organization_id, group_id, assignee_id, priority, type, status, tags, custom_fields[{id, value}], external_id, ticket_form_id, brand_id | id, url, created_at, updated_at, observed{status, priority, type, group_id, assignee_id, organization_id, requester_id, tags} |
| `Group` | name, description, is_public | id, url, default, deleted, created_at, updated_at |
| `Organization` | name, details, notes, external_id, group_id, domain_names, tags, organization_fields, ticket_restriction, shared_comments | id, url, created_at, updated_at |
| `TicketField` | type, title, description, agent_description, active, required, title_in_portal, visible_in_portal, editable_in_portal, required_in_portal, position, regexp_for_validation, tag, custom_field_options[{name, value, default}] | id, url, key, created_at, updated_at |

Every resource CR also gets `spec.configurationRef`.

## Generated Configuration kinds (`zendesk.krateo.io/v1alpha1`)

`TicketConfiguration`, `GroupConfiguration`, `OrganizationConfiguration`,
`TicketFieldConfiguration`, each with:

```yaml
spec:
  authentication:
    basic:
      usernameRef: {name: <secret>, namespace: <ns>, key: username}   # "<agent-email>/token"
      passwordRef: {name: <secret>, namespace: <ns>, key: password}   # the API token
```
