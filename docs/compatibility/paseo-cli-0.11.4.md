# Paseo CLI metadata compatibility

Installed 0.11.4 static source audited; no user timeline or credentials read.
`paseo ls --global --json` returns an array (id/status/cwd and unused fields).
`paseo inspect UUID --json` returns an object (Id/Cwd/Status/PendingPermissions/UpdatedAt).
There is no public `--cwd` option in this version. Filter normalized directory ancestry
inside the adapter before emitting any row. Unknown shape fails; unknown lifecycle
is unknown. Never infer task success from idle/closed or usage data.

Source SHA256:
- commands/agent/ls.js: d63545cc866ac1b68159d4dae16bf720c03a9eea434768f8005d63be7b371f17
- commands/agent/inspect.js: 04ce73aca8f49ecbe43302cee5d203e8b46f09a3af676c7a8a97288811d68040
- output/json.js: 1014d8da8bda6d27e45e57a8818abf491309fa365ce9c271d5f4d58491026bf6

These identify audited sources, not an identical-byte installation requirement.
Other versions need shape/behavior compatibility checks before being claimed supported.
