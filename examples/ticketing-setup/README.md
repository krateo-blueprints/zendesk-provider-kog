---
type: Example
title: ticketing-setup — from credentials to a categorised ticket
description: The four zendesk.krateo.io kinds applied in dependency order — credentials and Configurations, a routing Group, a tenant Organization, a category TicketField, then a Ticket that references all three by their server-assigned ids.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [example, zendesk, ticket, group, organization, ticketfield]
timestamp: 2026-10-31T00:00:00Z
---

# ticketing-setup

Prerequisite: the chart is installed with `zendeskSubdomain` set (see [usage](../../docs/usage.md)).

## 1. Credentials (once)

```console
$ kubectl create secret generic zendesk-oauth-client -n krateo-system \
    --from-literal=client_id='<OAUTH_CLIENT_IDENTIFIER>' \
    --from-literal=client_secret='<OAUTH_CLIENT_SECRET>'
$ kubectl label secret zendesk-oauth-client -n krateo-system external-secrets.io/type=webhook
$ helm upgrade --install zendesk-provider-kog <chart> -n krateo-system \
    --set zendeskSubdomain=<subdomain> --set oauth.rotation.enabled=true
$ kubectl apply -f chart/samples/configurations.yaml   # the 4 <Kind>Configuration CRs
```

## 2. Routing target and tenant

```console
$ kubectl apply -f chart/samples/test-group.yaml
$ kubectl get groups.zendesk.krateo.io test-group-platform-support -n krateo-system -o jsonpath='{.status.id}'
$ kubectl apply -f chart/samples/test-organization.yaml   # optionally set group_id to the id above
```

## 3. Category taxonomy

```console
$ kubectl apply -f chart/samples/test-ticketfield.yaml
$ kubectl get ticketfields.zendesk.krateo.io test-ticketfield-category -n krateo-system -o jsonpath='{.status.id}'
```

The options are sent once. Editing `custom_field_options` on the CR afterwards does nothing: Zendesk's
update would replace options by id and could strip categories from tickets
([configuration](../../docs/configuration.md#ticketfield)).

## 4. A ticket

Fill `organization_id`, `group_id` and `custom_fields[0].id` in `chart/samples/test-ticket.yaml` from the
ids above, then:

```console
$ kubectl apply -f chart/samples/test-ticket.yaml
$ kubectl get tickets.zendesk.krateo.io test-ticket-example -n krateo-system -o jsonpath='{.status.observed}'
```

`status.observed` shows the ticket's live status, priority, group and assignee as the help desk changes
them. Only `subject` and `external_id` are reconciled from the CR.

## Clean up

Delete the CRs in reverse order. The ticket is soft-deleted (recoverable for 30 days); the group is
marked deleted; the organization and ticket field are deleted outright.
