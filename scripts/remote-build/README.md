# Private proxy builds

Run `proxy-build.py ROOT JOB fetch|test|build|baseline|format` on the authorized remote host. ROOT must have an existing `build-scope.json`; JOB is a provisioned private directory under `ROOT/jobs` with `source`, `overlay/usr`, `home`, `runtime` and verified `packages.json`.

Provision the overlay from signed Arch packages (Rust, lld, Node.js and dependencies), checking signatures against the Arch keyring and package hashes before extraction. No host packages are installed. Cargo fetch alone has network access; compilation and tests use bubblewrap without host network or session access. Dependencies are pinned by Cargo.lock. Logs and source hashes remain inside the job. Run builds with two compiler jobs; do not fall back to tablet compilation if the remote host is unavailable.

Copy only public project sources into `source`; never upload private subscriptions, databases, credentials or device records. Fetch the resulting binary and compare SHA-256 on both machines before local runtime checks. The scope marker prevents operator mistakes; it does not make the SSH account a security sandbox.

For deliberate dependency changes, `resolve` generates a new Cargo.lock in the remote source directory. Fetch and review that lock before `fetch`; all build/test phases continue to use `--locked --offline`. The `qml` phase runs only native UI tests. Subscription fixtures and test nodes are fictional.
