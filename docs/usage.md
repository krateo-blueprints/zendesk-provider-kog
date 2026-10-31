---
type: Usage
title: zendesk-provider-kog — usage
description: How to run the provider — install it as a Krateo component with the Zendesk subdomain, provision the API-token Secret and one Configuration per kind, create Organization, Group, TicketField and Ticket CRs in dependency order, and verify the generated CRDs and controllers.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [krateo, install, oasgen-provider, zendesk]
timestamp: 2026-10-31T00:00:00Z
---

# Usage

## Prerequisite

A Krateo cluster with `oasgen-provider` **≥ 0.33.0** (post-delete verification honouring
`notFoundBody`, which Group relies on). Also used: `requestTransform` (≥ 0.17.0) and
`compareScope: updatable` (≥ 0.23.0).

## Install

As a Krateo component: the core-provider CDC derives the component CRD from
`chart/values.schema.json`. Set `zendeskSubdomain` (required) and, if needed, `resourceGroup`.

For local development only:

```console
$ helm upgrade --install zendesk-provider-kog ./chart -n krateo-system \
    --set zendeskSubdomain=<your-subdomain>
```

## Credentials

Zendesk API tokens authenticate with HTTP basic: username `<agent-email>/token`, password the token.
Create the Secret (placeholders shown, never commit real values) and the Configurations:

```console
$ kubectl create secret generic zendesk-api-token -n krateo-system \
    --from-literal=username='<agent-email>/token' \
    --from-literal=password='<YOUR_ZENDESK_API_TOKEN>'
$ kubectl apply -f chart/samples/configurations.yaml
```

Use an admin agent's token (groups, ticket fields and organizations are admin-managed).

## Drive the kinds

Server-assigned ids flow from one CR's `status.id` into the next CR's spec, so apply in this order:

1. `Group` (`chart/samples/test-group.yaml`): gives `status.id`, the routing target.
2. `Organization` (`test-organization.yaml`): optional `group_id` from step 1.
3. `TicketField` (`test-ticketfield.yaml`): the category drop-down; `status.id` is the custom field id.
4. `Ticket` (`test-ticket.yaml`): `organization_id`, `group_id` and
   `custom_fields: [{id, value}]` from steps 1–3.

## Verify

```console
$ kubectl get restdefinitions -n krateo-system
$ kubectl get crds | grep zendesk.krateo.io
$ kubectl get tickets.zendesk.krateo.io -n krateo-system -o yaml   # status.id, status.observed
```

A kind whose update keeps failing reports `DriftNotConverging` with the field named. Typical causes:
editing a closed ticket, or a token without the rights to change the field.
