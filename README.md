# zendesk-provider-kog

## What is this

A Krateo **KOG** (Krateo OpenAPI Generation) provider, built on
[`oasgen-provider`](https://github.com/krateo-platformops/oasgen-provider) **≥ 0.33.0**,
that exposes the ticketing surface of the Zendesk Support API as four Kubernetes kinds under the
`zendesk.krateo.io` group. Each kind is listed by its create endpoint; get/update/delete sit on the
matching item path.

| Kind | Zendesk API | Purpose | Reconciled after create |
|------|-------------|---------|-------------------------|
| `Organization` | `POST /api/v2/organizations` | one organization per tenant (keyed by `external_id`) | `name`, `details`, `notes`, `external_id`, `group_id` |
| `Group` | `POST /api/v2/groups` | an agent group: the routing target for a category of tickets | `name`, `description` |
| `TicketField` | `POST /api/v2/ticket_fields` | a custom ticket field, e.g. a drop-down category taxonomy | `title`, `description`, `agent_description`, `active`, `required` |
| `Ticket` | `POST /api/v2/tickets` | file a ticket (subject, first comment, requester, initial routing) | `subject`, `external_id` |

Every other spec field is **create-only**: sent once, at creation, and never compared or re-sent. That
is the whole design, and the reasons are per field in `chart/assets/<kind>.yaml`; the short version:

- **Ticket.** `comment` is write-only, and on an update Zendesk *adds* it as a new comment, so
  re-sending it would post a duplicate on every reconcile. `status`, `priority`, `type`, `group_id`
  and `assignee_id` are the help desk's triage: they are set as the initial routing, then agents and
  business rules own them. Comparing them would revert every reassignment, and a ticket closes
  automatically after it is solved, so a compared `status` could never converge. `tags` and
  `custom_fields` are rewritten by triggers and drop-down fields, and `custom_fields` comes back
  listing every field on the form. The live values are mirrored read-only under `status.observed`.
- **TicketField.** `custom_field_options` (the categories) is not reconciled. Zendesk's update
  *replaces options by id*: an option sent without its server-assigned id is created anew, and an
  option left out is deleted **together with its value on every ticket**. A `RestDefinition` cannot
  carry those ids from status into the request, so sending the spec's options on an update could strip
  categories from live tickets.
- **Group.** `is_public` is create-only, because Zendesk cannot make a private group public.
- **Organization.** `domain_names`, `tags`, `organization_fields`, `ticket_restriction` and
  `shared_comments` are create-only. Zendesk normalises, merges or couples them, so they do not read
  back as written.

The per-kind identifiers, verbs and `compareScope` are in
[docs/configuration.md](docs/configuration.md); the reasoning behind each choice is in the
`chart/templates/rd-<kind>.yaml` comments.

**Zendesk's body envelope.** Zendesk wraps every body: `{"ticket": {...}}`, `{"group": {...}}`, and so
on. The assets declare the *unwrapped* object (the shape of the CR), and each `RestDefinition` restores
the envelope at the wire: a `requestTransform` (`{ticket: .}`) on create/update, and a
`responseTransform` that unwraps every create/get/update response. The official wrapper is not kept in
the assets because the controller filters an outgoing body by top-level key only. With a declared
wrapper, the whole object (`comment` included) would pass that filter on every update. This is a
documented deviation from Zendesk's OpenAPI document, enforced by `hack/assert-drift-invariants.py`.

The chart ships 4 `RestDefinition`s + the trimmed OpenAPI spec each references (as a `ConfigMap`), and
nothing else: **no runtime component of its own**, no Deployment, no Service, no image, no proxy.
`oasgen-provider` watches the RestDefinitions, generates the CRDs under `zendesk.krateo.io`, and
auto-deploys a `rest-dynamic-controller` per kind. See [docs/overview.md](docs/overview.md).

## Install

Prerequisite: a Krateo cluster with `oasgen-provider` **≥ 0.33.0**. It provides
`restdefinitions.ogen.krateo.io`, and 0.33.0 is where the controller's post-delete verification honours
`notFoundBody`, which `Group` relies on (Zendesk soft-deletes groups). The other features used are
older: `requestTransform` 0.17.0, `compareScope: updatable` 0.23.0.

Per the Krateo "everything is a Composition" rule, this chart is installed as a **component** (a
`CompositionDefinition` the core-provider CDC derives from `values.schema.json`), not via
`helm install`. See [docs/usage.md](docs/usage.md).

For local development against a kind cluster only:

```console
$ helm upgrade --install zendesk-provider-kog ./chart --namespace krateo-system \
    --set zendeskSubdomain=<your-subdomain>
```

## Configure

The chart surface is two scalars:

| Value | Default | Meaning |
|-------|---------|---------|
| `resourceGroup` | `zendesk.krateo.io` | the API group the generated CRDs land under |
| `zendeskSubdomain` | `""` (**required**) | the `<subdomain>` of `https://<subdomain>.zendesk.com`; rendering fails while it is empty or not a DNS label |

The subdomain is a chart value, not a per-Configuration field, because `rest-dynamic-controller` sends
every call to the OpenAPI document's `servers[0].url` **verbatim**. It does not substitute server
variables, and a Configuration CR can only supply path/query/header/cookie parameters, never the host.
So the chart's ConfigMaps replace the official URL template `https://{subdomain}.{domain}.com` at render
time, and **one install targets one Zendesk account**. For a second account, install again under
another release name *and* another `resourceGroup`.

Authentication is an **OAuth access token sent as a bearer token**. Zendesk is removing API tokens (no
new tokens from late October 2026, all deactivated on 30 April 2027), so the provider uses the
`client_credentials` grant. Those access tokens **expire** (30 minutes by default, 48 hours at most) and
no refresh token is issued, so the token Secret is kept fresh by the **External Secrets Operator**
(ESO ≥ 2.x, required when `oauth.rotation.enabled`). The chart ships an ESO `Webhook` generator that
POSTs to `https://<subdomain>.zendesk.com/oauth/tokens` and an `ExternalSecret` that rewrites the
token Secret every `oauth.rotation.refreshInterval`. rest-dynamic-controller reads the Secret on every
reconcile, so a rotated token applies without a restart.

Each asset declares an HTTP bearer scheme, so oasgen generates a per-kind `<Kind>Configuration` CRD
with `spec.authentication.bearer.tokenRef` and adds `spec.configurationRef` to every resource CR.
Create a **confidential OAuth client** (Admin Center > Apps and integrations > APIs > OAuth clients),
then:

```console
$ kubectl create secret generic zendesk-oauth-client -n krateo-system \
    --from-literal=client_id='<OAUTH_CLIENT_IDENTIFIER>' \
    --from-literal=client_secret='<OAUTH_CLIENT_SECRET>'
$ kubectl label secret zendesk-oauth-client -n krateo-system external-secrets.io/type=webhook
$ helm upgrade --install zendesk-provider-kog <chart> -n krateo-system \
    --set zendeskSubdomain=<subdomain> --set oauth.rotation.enabled=true
$ kubectl apply -f chart/samples/configurations.yaml   # the 4 <Kind>Configuration CRs
```

All four Configurations may share one name (`zendesk-config`); the kind is implied by the resource
that references it. The OAuth client must act as an **admin**: groups, ticket fields and
organizations are admin-managed, and Zendesk answers an under-privileged organization edit with a 200
while ignoring it.
Full surface: [docs/configuration.md](docs/configuration.md).

## Examples

- [examples/ticketing-setup](examples/ticketing-setup/README.md): the credential wiring, then an
  Organization, a Group, a category TicketField and a Ticket, applied in dependency order.
- `chart/samples/`: the 4 `<Kind>Configuration` CRs and one applyable test CR per kind
  (`test-<kind>.yaml`).

## Docs

The full documentation bundle follows the Krateo Documentation Standard:

- [docs/index.md](docs/index.md): the map of the bundle.
- [docs/overview.md](docs/overview.md): how it works (RestDefinitions → CRDs + controllers, the
  envelope transforms).
- [docs/usage.md](docs/usage.md): install, provision auth, drive the kinds, verify.
- [docs/configuration.md](docs/configuration.md): values, per-kind mappings, the compared/create-only
  tables, invariants.
- [docs/api.md](docs/api.md): the generated CRDs and the CompositionDefinition.
- [docs/examples.md](docs/examples.md): the runnable examples.
- [docs/release.md](docs/release.md): how a release ships.
- [docs/log.md](docs/log.md): curated history.
- [docs/llms.txt](docs/llms.txt): the file-by-file index.

## Develop & release

- **Chart.** `chart/` is the single first-class chart; `chart/values.schema.json` types its values
  (and is what the CDC derives the component CRD from).
- **Release.** One plain-semver tag (`X.Y.Z`, no `v`) drives `release-oci.yaml`, which stamps
  `CHART_VERSION` and packages `chart/` to `oci://ghcr.io/krateo-blueprints/charts`. The chart is the
  only release artifact. Details: [docs/release.md](docs/release.md).
- **CI.** `lint.yaml` runs the shared `lint-docs` check, `hack/assert-drift-invariants.py` (every
  create-only absence, the envelope transforms, `compareScope: updatable`), and `helm lint`/`template`
  with a placeholder subdomain. `preflight-refs.yaml` resolves chart/image references, and
  `security.yml` runs the shared org security workflow.

## License

Apache-2.0. See [LICENSE](LICENSE).
