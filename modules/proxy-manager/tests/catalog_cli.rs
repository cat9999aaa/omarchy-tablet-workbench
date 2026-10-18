use serde_json::{Value, json};
use std::{
    fs,
    io::Write,
    process::{Command, Stdio},
};
fn call(root: &std::path::Path, data: Value) -> Value {
    let mut p = Command::new(env!("CARGO_BIN_EXE_omt-proxy"))
        .args(["catalog", root.to_str().unwrap()])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .unwrap();
    p.stdin
        .take()
        .unwrap()
        .write_all(serde_json::to_string(&data).unwrap().as_bytes())
        .unwrap();
    let out = p.wait_with_output().unwrap();
    serde_json::from_slice(&out.stdout).unwrap_or(json!({"missing":true}))
}
#[test]
fn explicit_preview_then_commit() {
    let root = std::env::temp_dir().join(format!("omt-cli-{}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    let empty = call(&root, json!({"action":"list"}));
    assert_eq!(empty["nodes"].as_array().unwrap().len(), 0);
    let p = call(
        &root,
        json!({"action":"preview-uri","text":"vless://11111111-2222-3333-4444-555555555555@proxy.example:443?security=tls#Example"}),
    );
    assert!(p["preview_id"].is_string());
    assert!(!p.to_string().contains("proxy.example"));
    let before = call(&root, json!({"action":"list"}));
    assert_eq!(before["nodes"].as_array().unwrap().len(), 0);
    let result = call(
        &root,
        json!({"action":"commit","preview_id":p["preview_id"],"confirmed":true}),
    );
    assert_eq!(result["nodes"].as_array().unwrap().len(), 1);
    assert!(result["current"].is_null());
    fs::remove_dir_all(root).unwrap();
}
