use serde_json::{Value, json};
use std::{
    io::Write,
    os::unix::fs::PermissionsExt,
    process::{Command, Stdio},
};
#[test]
fn preview_is_private_checked_and_does_not_activate() {
    let root = std::env::temp_dir().join(format!("omt-core-cli-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    let store = omt_proxy::storage::Store::open(&root).unwrap();
    let node=omt_proxy::catalog::import_preview(b"vless://11111111-2222-3333-4444-555555555555@127.0.0.1:24443?security=tls&type=ws&sni=localhost&path=%2Fws#Fixture",omt_proxy::catalog::ImportFormat::Uri).unwrap().nodes.remove(0);
    store
        .write(
            "catalog.json",
            &serde_json::to_vec(&json!({"revision":1,"nodes":[node],"current":null})).unwrap(),
        )
        .unwrap();
    store.write("template.json", b"{}").unwrap();
    drop(store);
    let request =
        json!({"mode":"rules","node_id":node.id,"base_revision":1,"rules":[],"port":10818});
    let mut child = Command::new(env!("CARGO_BIN_EXE_omt-proxy"))
        .args(["core-preview", root.to_str().unwrap()])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(request.to_string().as_bytes())
        .unwrap();
    let out = child.wait_with_output().unwrap();
    assert!(
        out.status.success(),
        "{}",
        String::from_utf8_lossy(&out.stdout)
    );
    let public: Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(public["applied"], false);
    assert_eq!(public["candidate_hash"].as_str().unwrap().len(), 64);
    assert!(!String::from_utf8_lossy(&out.stdout).contains("11111111"));
    let cfg = root.join("candidate.json");
    assert_eq!(
        std::fs::metadata(&cfg).unwrap().permissions().mode() & 0o777,
        0o600
    );
    let v: Value = serde_json::from_slice(&std::fs::read(cfg).unwrap()).unwrap();
    assert_eq!(v["inbounds"][0]["port"], 10818);
    assert!(!root.join("active.json").exists());
    std::fs::remove_dir_all(root).unwrap();
}
#[test]
fn applied_selection_requires_matching_active_hash() {
    use sha2::{Digest, Sha256};
    let root = std::env::temp_dir().join(format!("omt-applied-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    let store = omt_proxy::storage::Store::open(&root).unwrap();
    store.write("active.json", b"working").unwrap();
    store.write("applied.json",serde_json::to_string(&json!({"sha256":format!("{:x}",Sha256::digest(b"working")),"node_id":"node","mode":"global"})).unwrap().as_bytes()).unwrap();
    drop(store);
    let v = omt_proxy::catalog_cli::run(&root, b"{\"action\":\"list\"}").unwrap();
    assert_eq!(v["applied"]["mode"], "global");
    let store = omt_proxy::storage::Store::open(&root).unwrap();
    store.write("active.json", b"restored").unwrap();
    drop(store);
    let v = omt_proxy::catalog_cli::run(&root, b"{\"action\":\"list\"}").unwrap();
    assert!(v["applied"].is_null());
    std::fs::remove_dir_all(root).unwrap();
}
