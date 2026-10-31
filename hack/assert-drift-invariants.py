#!/usr/bin/env python3
"""Assert the drift-reconciliation invariants that exist only as ABSENCES in the OAS assets and as
small, easily-deleted lines in the RestDefinitions.

Every Zendesk kind here is safe for one structural reason and one behavioural one, and neither leaves a
trace in the generated CRD. Both are one careless edit from being undone, with no error and nothing
failing — until a live help desk starts receiving the consequences.

How the controller works, so a future reader can check this file still asserts the right thing
(rest-dynamic-controller, now in the oasgen-provider monorepo: builder/builder.go, clienttools.go,
controllers/helpers.go, fieldmapping/fieldmapping.go):

  * `compareScope: updatable` derives the compare set from the UPDATE verb's declared request body
    (UpdatableBodyPaths, leaf paths). A field absent from that body is never compared. The default is
    `fullSpec`, under which every spec key the GET echoes is compared — and Zendesk echoes almost
    everything — so DELETING the compareScope line is the same regression as re-adding a field.
  * The outgoing body is filtered to the properties the operation declares, by TOP-LEVEL KEY ONLY
    (processFields). That is what makes a create-only field create-only. It is also why the assets
    declare Zendesk's bodies UNWRAPPED: with the official {"ticket": {...}} wrapper declared, the update
    body has one top-level key, the whole spec object passes the filter, and the write-only `comment`
    is re-sent — i.e. POSTED AGAIN AS A NEW COMMENT — on every drift-triggered update.
  * processFields runs over STATUS as well as spec, so a status field that shares a name with a
    request-body property is copied into that request whenever the spec omits it.
  * requestTransform runs after the body is assembled (create/update/delete); responseTransform runs on
    the raw create/get/update response before status population and comparison. Status is CLEARED and
    repopulated from the create and update responses, so an unwrapped get alone is not enough.

The concrete hazards each rule below prevents:

  Ticket       `comment` on update        -> a duplicate public comment to the requester per reconcile
               triage fields compared     -> the controller reverts agents' reassignment/escalation;
                                             `status` additionally loops forever once a ticket closes
               tags / custom_fields       -> fights triggers and drop-down tags; shape never matches
  TicketField  custom_field_options       -> replace-by-id PUT re-creates every option and strips the
               on update                     category value from existing tickets, on ANY drift
  Group        is_public on update        -> private->public is impossible: eternal drift
  Organization list/map/coupled fields    -> normalised or feature-coupled, never read back as written

Exit 1 if any invariant is broken.
"""
import re
import sys

import yaml

PLACEHOLDER = "https://{subdomain}.{domain}.com"

# kind -> where it lives and what Zendesk wraps it in
KINDS = {
    "Ticket": {
        "asset": "chart/assets/ticket.yaml",
        "rd": "chart/templates/rd-ticket.yaml",
        "wrapper": "ticket",
        "collection": "/api/v2/tickets",
        "item": "/api/v2/tickets/{ticket_id}",
    },
    "Group": {
        "asset": "chart/assets/group.yaml",
        "rd": "chart/templates/rd-group.yaml",
        "wrapper": "group",
        "collection": "/api/v2/groups",
        "item": "/api/v2/groups/{group_id}",
    },
    "Organization": {
        "asset": "chart/assets/organization.yaml",
        "rd": "chart/templates/rd-organization.yaml",
        "wrapper": "organization",
        "collection": "/api/v2/organizations",
        "item": "/api/v2/organizations/{organization_id}",
    },
    "TicketField": {
        "asset": "chart/assets/ticketfield.yaml",
        "rd": "chart/templates/rd-ticketfield.yaml",
        "wrapper": "ticket_field",
        "collection": "/api/v2/ticket_fields",
        "item": "/api/v2/ticket_fields/{ticket_field_id}",
    },
}

# The update body must be EXACTLY this set: it is the compared set under `updatable`, so it IS the drift
# contract. Widening it is a design decision that has to be made here, deliberately, with a reason.
COMPARED = {
    "Ticket": {"subject", "external_id"},
    "Group": {"name", "description"},
    "Organization": {"name", "details", "notes", "external_id", "group_id"},
    "TicketField": {"title", "description", "agent_description", "active", "required"},
}

# CREATE-ONLY: must stay in the create body (so the CR can still set it) and out of the update body.
CREATE_ONLY = {
    "Ticket": {
        "comment": "write-only; on update Zendesk ADDS it as a new comment — a duplicate per reconcile",
        "status": "agent/automation-owned; solved->closed is automatic and a closed ticket rejects every "
                  "update (422), so a compared status can never converge",
        "group_id": "help-desk triage: comparing it reverts every reassignment",
        "assignee_id": "help-desk triage: comparing it reverts every reassignment",
        "priority": "help-desk triage: comparing it reverts every escalation",
        "type": "help-desk triage",
        "tags": "triggers and drop-down fields add tags; update REPLACES the set",
        "custom_fields": "response lists every field on the form (length/order differ): permanent drift",
        "requester": "write-only object (response carries requester_id)",
        "requester_id": "re-assigning the requester from drift is never intended",
        "organization_id": "must match the requester's membership; owned by the help desk afterwards",
    },
    "Group": {
        "is_public": "a private group cannot be made public: drift no update can fix",
    },
    "Organization": {
        "domain_names": "destructive replace on update, normalised by Zendesk",
        "tags": "destructive replace, normalised, ignored without an account feature",
        "organization_fields": "merge semantics and typed values: does not read back as written",
        "ticket_restriction": "coupled to shared_tickets/shared_comments and account features",
        "shared_comments": "reset by Zendesk whenever tickets are not shared",
    },
    "TicketField": {
        "custom_field_options": "update is REPLACE-BY-ID: options without ids are re-created and omitted "
                                "ones removed WITH their values on tickets — destructive on any drift",
        "type": "immutable after creation",
        "position": "re-laid-out by ticket forms",
        "visible_in_portal": "portal flags are interdependent; coercion undocumented",
        "editable_in_portal": "portal flags are interdependent; coercion undocumented",
        "required_in_portal": "portal flags are interdependent; coercion undocumented",
        "title_in_portal": "portal flags are interdependent; coercion undocumented",
    },
}

# EXCLUDED: modelled nowhere — in neither the create nor the update body.
EXCLUDED = {
    "Ticket": {
        "description": "silently ignored on update; the first comment is set via `comment`",
        "raw_subject": "overrides `subject` when set: two sources of truth for one field",
    },
    "Group": {
        "default": "account-wide singleton: two CRs would fight over it",
    },
    "Organization": {
        "shared_tickets": "deprecated, and coupled to ticket_restriction",
    },
    "TicketField": {
        "raw_title": "dynamic-content source; the rendered title is what comes back",
        "sub_type_id": "system fields only",
    },
}

# Status names must not collide with request-body names (processFields copies status into requests).
# Group's notFoundBody is load-bearing: groups are soft-deleted.
REQUIRED_NOT_FOUND_BODY = {"Group": ".deleted"}

HELM_ACTION = re.compile(r"\{\{.*?\}\}")


def load_rd(root, path):
    with open("%s/%s" % (root, path)) as fh:
        text = fh.read()
    # The RD templates use only simple value substitutions; neutralise them to parse the YAML.
    return text, yaml.safe_load(HELM_ACTION.sub("X", text))


def body_props(doc, path, method):
    op = (doc.get("paths", {}).get(path) or {}).get(method)
    if op is None:
        return None
    schema = (op.get("requestBody") or {}).get("content", {}).get("application/json", {}).get("schema", {})
    schema = resolve(doc, schema)
    return set((schema.get("properties") or {}).keys())


def response_props(doc, path, method, code):
    op = (doc.get("paths", {}).get(path) or {}).get(method) or {}
    schema = ((op.get("responses") or {}).get(code) or {}).get("content", {}).get(
        "application/json", {}).get("schema", {})
    return set((resolve(doc, schema).get("properties") or {}).keys())


def resolve(doc, schema):
    ref = (schema or {}).get("$ref")
    if not ref:
        return schema or {}
    node = doc
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return resolve(doc, node)


def main(root="."):
    failures = []

    def fail(msg):
        failures.append(msg)

    for kind, k in KINDS.items():
        asset, rdpath, w = k["asset"], k["rd"], k["wrapper"]
        with open("%s/%s" % (root, asset)) as fh:
            raw_asset = fh.read()
        doc = yaml.safe_load(raw_asset)
        rd_text, rd = load_rd(root, rdpath)
        res = rd["spec"]["resource"]
        verbs = {v["action"]: v for v in res.get("verbsDescription", [])}

        create = body_props(doc, k["collection"], "post")
        update = body_props(doc, k["item"], "put")
        if create is None or update is None:
            sys.exit("%s: create (POST %s) or update (PUT %s) operation missing — this guard is stale, "
                     "fix it deliberately" % (asset, k["collection"], k["item"]))

        # 1. compareScope: updatable, exactly once. The default (fullSpec) re-admits everything.
        scopes = [ln.split(":", 1)[1].strip() for ln in rd_text.splitlines()
                  if ln.strip().startswith("compareScope:")]
        if scopes != ["updatable"]:
            fail("%s: %s must declare exactly `compareScope: updatable`, found %s. The default IS fullSpec, "
                 "so deleting the line re-admits every echoed field to the drift set." % (rdpath, kind, scopes or "none"))

        # 2. The update body is exactly the compared set.
        if update != COMPARED[kind]:
            fail("%s: %s update body is %s, expected exactly %s. The update body IS the compared set under "
                 "`updatable`; change COMPARED in this script only as a deliberate, reasoned decision."
                 % (asset, kind, sorted(update), sorted(COMPARED[kind])))

        # 3. Create-only fields: out of update, still in create.
        for field, why in CREATE_ONLY[kind].items():
            if field in update:
                fail("%s: `%s` is back in the %s UPDATE body.\n    %s\n    It must stay create-only."
                     % (asset, field, kind, why))
            if field not in create:
                fail("%s: `%s` is missing from the %s CREATE body, so it is no longer a CR spec field and "
                     "cannot be set even at creation." % (asset, field, kind))

        # 4. Excluded fields: nowhere.
        for field, why in EXCLUDED[kind].items():
            if field in create or field in update:
                fail("%s: `%s` must not be modelled on %s at all: %s" % (asset, field, kind, why))

        # 5. No wrapper in any declared body: top-level filtering is the create-only mechanism.
        for name, props in (("create", create), ("update", update),
                            ("get response", response_props(doc, k["item"], "get", "200"))):
            if w in props:
                fail("%s: the `%s` wrapper is declared in the %s %s schema. Bodies are declared UNWRAPPED: "
                     "with a wrapper, the controller's top-level filter passes the whole object and "
                     "create-only fields (Ticket `comment`!) are re-sent on every update."
                     % (asset, w, kind, name))
        if "id" not in response_props(doc, k["item"], "get", "200"):
            fail("%s: the %s GET response schema must expose `id` at the top level (the identifier)." % (asset, kind))

        # 6. Wire envelope restored by the RD.
        want_req = "{%s: .}" % w
        for action in ("create", "update"):
            v = verbs.get(action) or {}
            got = ((v.get("requestTransform") or {}).get("inline") or "").strip()
            if got != want_req:
                fail("%s: %s %s must carry requestTransform `%s` (Zendesk rejects an unwrapped body), "
                     "found %r." % (rdpath, kind, action, want_req, got or None))
        for action in ("get", "delete"):
            if (verbs.get(action) or {}).get("requestTransform"):
                fail("%s: %s %s must NOT carry a requestTransform (on delete it would send %s on a DELETE)."
                     % (rdpath, kind, action, want_req))
        progs = {}
        for action in ("create", "get", "update"):
            prog = (((verbs.get(action) or {}).get("responseTransform") or {}).get("inline") or "").strip()
            if ".%s" % w not in prog:
                fail("%s: %s %s must carry the unwrap responseTransform (.%s). Status is cleared and "
                     "repopulated from the %s response; without the unwrap status.id is lost and the next "
                     "observe cannot address the resource." % (rdpath, kind, action, w, action))
            progs[action] = prog
        if len(set(progs.values())) != 1:
            fail("%s: %s responseTransform must be byte-identical on create/get/update (status must have "
                 "one shape whichever verb wrote it)." % (rdpath, kind))

        # 7. Status / identifier names never collide with request-body properties.
        status_fields = list(res.get("identifiers", [])) + list(res.get("additionalStatusFields", []))
        for sf in status_fields:
            top = sf.split(".", 1)[0]
            if top in create or top in update:
                fail("%s: %s status field `%s` shares its name with a request-body property; the controller "
                     "copies status into the request whenever the spec omits the field (e.g. a re-created "
                     "ticket filed as `closed`). Expose it under another name." % (rdpath, kind, sf))

        # 8. Every verb's path/method exists in the asset; mapped path params exist on the path.
        for action, v in verbs.items():
            path, method = v["path"], v["method"].lower()
            if method not in (doc.get("paths", {}).get(path) or {}):
                fail("%s: %s %s -> %s %s is not an operation in %s." % (rdpath, kind, action, v["method"], path, asset))
            for fm in v.get("fieldMapping", []) + v.get("requestFieldMapping", []):
                if fm.get("inPath") and "{%s}" % fm["inPath"] not in path:
                    fail("%s: %s %s maps path parameter `%s`, which %s does not have."
                         % (rdpath, kind, action, fm["inPath"], path))

        # 9. The server URL template the ConfigMap substitutes — exactly once, as servers[0].url.
        if raw_asset.count(PLACEHOLDER) != 1 or (doc.get("servers") or [{}])[0].get("url") != PLACEHOLDER:
            fail("%s: servers[0].url must be the official template %s, present exactly once; the chart "
                 "substitutes it with the configured subdomain." % (asset, PLACEHOLDER))

        # 10. Auth is an OAuth bearer token, and only that. Zendesk API tokens (http/basic) are being
        #     removed (all deactivated 30 Apr 2027); re-adding basic auth would ship a dead credential path.
        schemes = (doc.get("components") or {}).get("securitySchemes") or {}
        if schemes != {"bearerAuth": {"type": "http", "scheme": "bearer"}}:
            fail("%s: securitySchemes must be exactly bearerAuth (http/bearer); found %s." % (asset, schemes))
        if doc.get("security") != [{"bearerAuth": []}]:
            fail("%s: top-level security must be exactly [bearerAuth]." % asset)

        # 11. Soft-delete tombstones.
        need = REQUIRED_NOT_FOUND_BODY.get(kind)
        if need:
            nfb = (((verbs.get("get") or {}).get("notFoundBody") or {}).get("inline") or "")
            if need not in nfb:
                fail("%s: %s get must declare a notFoundBody testing `%s`: %s resources are soft-deleted, and without "
                     "it the post-delete verification holds the CR's finalizer forever." % (rdpath, kind, need, kind))

    if failures:
        print("drift-invariant check FAILED:\n")
        for f in failures:
            print("  - %s\n" % f)
        return 1
    print("drift invariants hold (%d kinds)." % len(KINDS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
