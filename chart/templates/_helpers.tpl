{{/*
zendesk.asset renders one OAS asset for its ConfigMap, with the server URL resolved.

rest-dynamic-controller sends every request to the document's servers[0].url VERBATIM: it does not
substitute OpenAPI server variables, and a Configuration CR cannot carry a host either (its
configurationFields reach path/query/header/cookie parameters only). So the Zendesk account is fixed per
chart install, here, by replacing the official URL template with https://<zendeskSubdomain>.zendesk.com.

Both guards fail the RENDER rather than shipping a document whose server is the literal template
"https://{subdomain}.{domain}.com" (which would fail every call at runtime, far from the cause):
  - zendeskSubdomain must be set and be a DNS label (no dots: it is the <subdomain> part only);
  - the asset must contain the URL template exactly once, so the replace cannot silently miss.

Usage: {{ include "zendesk.asset" (dict "root" . "file" "assets/ticket.yaml") }}
*/}}
{{- define "zendesk.asset" -}}
{{- $root := .root -}}
{{- $raw := $root.Files.Get .file -}}
{{- $placeholder := "https://{subdomain}.{domain}.com" -}}
{{- $sub := required "zendeskSubdomain is required: the <subdomain> of https://<subdomain>.zendesk.com (no scheme, no dots)" $root.Values.zendeskSubdomain -}}
{{- if not (regexMatch "^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$" $sub) -}}
{{- fail (printf "zendeskSubdomain %q is not a DNS label: give only the <subdomain> part of https://<subdomain>.zendesk.com" $sub) -}}
{{- end -}}
{{- $n := len (regexFindAll (regexQuoteMeta $placeholder) $raw -1) -}}
{{- if ne $n 1 -}}
{{- fail (printf "%s must contain the server URL template %q exactly once (found %d); the ConfigMap substitutes it" .file $placeholder $n) -}}
{{- end -}}
{{- replace $placeholder (printf "https://%s.zendesk.com" $sub) $raw -}}
{{- end -}}
