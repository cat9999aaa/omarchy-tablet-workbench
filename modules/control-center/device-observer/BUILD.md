# Panel-owned device observer

Source: this repository, `modules/control-center/device-observer`; original code,
GPL-3.0-only (repository `LICENSE`). Rust 2021, minimum Rust 1.77; standard library
only. Cargo.lock fixes the empty external dependency graph. Links system libudev
(LGPL-2.1-or-later, supplied by the OS), libc and the compiler runtime; those
shared libraries are not bundled or replaced.

```sh
cargo test --manifest-path modules/control-center/device-observer/Cargo.toml --locked --offline
cargo build --release --manifest-path modules/control-center/device-observer/Cargo.toml --locked --offline
```

Build on the authorized isolated build host, without `-march=native`. Install the
verified executable as `bin/pcadmin-device-observer` inside the same versioned
plugin payload as Panel.qml, mode 0755. Record source commit, compiler version,
OS ABI package versions, binary SHA256 and dynamic dependencies alongside the
candidate. Keep generated binaries out of Git. Compare target ABI before install.
There is no runtime download, unit, timer or standalone auto-start.

The existing UI publisher preserves file modes when copying this internal
helper. This is not permission to update the global proxy, input method or other
backends. The compatible Python helper must precede the UI pointer switch;
rollback restores the UI first and the helper second. The root touch-cache
producer and existing services are outside this change.

Output is only schema 1 ready/changed/lost NDJSON. Monitor enable precedes ready;
input subsystem notifications carry no attributes, node names or input contents.
Closing stdout wakes an idle observer; the panel terminates and reaps its owned
process. Loss is terminal until an explicit refresh or reopen.
