---
type: ExampleIndex
title: zendesk-provider-kog — examples
description: Index of the runnable examples — the ticketing-setup walkthrough and the sample CR for each of the four kinds under chart/samples/, with the order they must be applied in.
resource: oci://ghcr.io/krateo-blueprints/charts/zendesk-provider-kog
tags: [examples, zendesk, samples]
timestamp: 2026-10-31T00:00:00Z
---

# Examples

- [examples/ticketing-setup](../examples/ticketing-setup/README.md): the whole flow, from credentials to a
  categorised ticket.
- [chart/samples/configurations.yaml](../chart/samples/configurations.yaml): the four
  `<Kind>Configuration` CRs (placeholder Secret instructions in the header).
- [chart/samples/test-group.yaml](../chart/samples/test-group.yaml): apply first.
- [chart/samples/test-organization.yaml](../chart/samples/test-organization.yaml)
- [chart/samples/test-ticketfield.yaml](../chart/samples/test-ticketfield.yaml)
- [chart/samples/test-ticket.yaml](../chart/samples/test-ticket.yaml): apply last; fill the commented
  ids from the other CRs' `status.id`.
