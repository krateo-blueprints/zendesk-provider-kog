---
type: Usage
title: zendesk-provider-kog — usage
description: How to run the provider — install it as a Krateo component with the Zendesk subdomain, provision the OAuth client Secret (the External Secrets Operator keeps the bearer token fresh) and one Configuration per kind, create Organization, Group, TicketField and Ticket CRs in dependency order, and verify the generated CRDs and controllers.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [krateo, install, oasgen-provider, zendesk]
timestamp: 2026-11-01T00:00:00Z
---

# Usage

## Prerequisite

A Krateo cluster with `oasgen-provider` **≥ 0.46.0**.

Before 0.46.0 ([oasgen-provider#347](https://github.com/krateo-platformops/oasgen-provider/issues/347)),
a create that Zendesk refuses (for example 422 *"Private groups are not enabled for this account"*)
latched the CR to `Ready=True` / `Available` after about two minutes, with no `status.id`: a resource
that does not exist reported Available. From 0.46.0 the CR stays `Creating` with `ReconcileError` and
never becomes Available. Check the installed oasgen-provider version (its image tag) before relying on
`Ready`.

Also used, all older: post-delete verification honouring `notFoundBody` (≥ 0.33.0, which Group relies
on), `compareScope: updatable` (≥ 0.23.0) and `requestTransform` (≥ 0.17.0).

## Install

As a Krateo component: the core-provider CDC derives the component CRD from
`chart/values.schema.json`. Set `zendeskSubdomain` (required) and, if needed, `resourceGroup`.

For local development only:

```console
$ helm upgrade --install zendesk-provider-kog ./chart -n krateo-system \
    --set zendeskSubdomain=<your-subdomain>
```

## Credentials

The provider authenticates with an OAuth access token (client_credentials grant) sent as a bearer
token; Zendesk API tokens are being removed (all deactivated 30 April 2027). Access tokens expire and
no refresh token is issued, so the External Secrets Operator keeps the token Secret fresh
(`oauth.rotation.enabled=true`; ESO ≥ 2.x must be installed). Create a confidential OAuth client in
Admin Center, then (placeholders shown; never commit real values):

```console
$ kubectl create secret generic zendesk-oauth-client -n krateo-system \
    --from-literal=client_id='<OAUTH_CLIENT_IDENTIFIER>' \
    --from-literal=client_secret='<OAUTH_CLIENT_SECRET>'
$ kubectl label secret zendesk-oauth-client -n krateo-system external-secrets.io/type=webhook
$ helm upgrade --install zendesk-provider-kog <chart> -n krateo-system \
    --set zendeskSubdomain=<subdomain> --set oauth.rotation.enabled=true
$ kubectl apply -f chart/samples/configurations.yaml   # the 4 <Kind>Configuration CRs
```

The OAuth client must act as an admin (groups, ticket fields and organizations are admin-managed).

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
