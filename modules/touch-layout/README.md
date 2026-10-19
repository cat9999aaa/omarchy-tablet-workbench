# Touch layout profile

On-demand theme dimensions for the existing Omarchy bar. No daemon or polling.
The first release accepts a pinned host, one active output, a bottom bar and the
managed DASHEN theme. Ambiguous outputs, unknown sources, overrides or overflow
refuse changes and preserve the existing layout.

`profile.py status|plan touch|plan compact|apply PLAN_ID|rollback TRANSACTION_ID`
uses fixed home-relative paths. Plans are recomputed under a lock at apply time.
Both theme source and generated current theme are compared before writes; failed
reloads restore only bytes still owned by this transaction. A concurrent edit is
preserved and reported as conflict. Compact restores the original theme bytes.

Deployment is one reviewed batch with navigation 0.1.6/control center 0.2.3:

- All non-test Python files and `host-source.json` in this directory.
- Sibling `control-center/Panel.qml` and `DeviceEntry.qml`, used by the isolated
  geometry probe; retain their original source hashes in the deployment receipt.
- The reversible `bar_compat.py` patch to the existing user-owned bar clone.
- EdgeGestures.qml, EdgeInput.qml, EdgePolicy.js and the existing Gesture.js and
  edge_menu.py together in the existing edge source directory.
- Navigation candidate helpers and its versioned UI bundle, plus the control
  center UI bundle. Preserve the existing device observer binary and provenance.

Do not modify packaged Omarchy files. Back up originals and recover in inverse
order, checking hashes before overwriting. The profile remains compact until an
explicit touch request succeeds; a saved record alone is not live verification.

Software gates on an isolated build host:

```
python3 scripts/acceptance/run.py --output /isolated/evidence/general
python3 scripts/acceptance/run.py --suite native-host --output /isolated/evidence/native
```

The native gate additionally requires pinned `/official` sources, Quickshell,
headless Sway and `C1_ISOLATED_TEST=1` in a fresh isolated namespace. Ordinary CI
covers portable Python/Node/Qt checks; it cannot replace the native gate.
Physical finger, pen and cold-start acceptance remain separate.
