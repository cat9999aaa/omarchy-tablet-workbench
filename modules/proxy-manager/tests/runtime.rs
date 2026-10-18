use omt_proxy::runtime::*;
use omt_proxy::storage::Store;
use serde_json::json;
#[test]
fn modified_candidate_and_live_port_fail_before_core() {
    let root = std::env::temp_dir().join(format!("omt-runtime-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    let store = Store::open(&root).unwrap();
    store.write("candidate.json", b"{}").unwrap();
    assert_eq!(
        candidate(&store, &"0".repeat(64)).unwrap_err(),
        "candidate_hash_conflict"
    );
    let data = serde_json::to_vec(&json!({"inbounds":[{"port":10808}]})).unwrap();
    store.write("candidate.json", &data).unwrap();
    use sha2::{Digest, Sha256};
    let hash = format!("{:x}", Sha256::digest(data));
    assert_eq!(
        candidate(&store, &hash).unwrap_err(),
        "candidate_listener_invalid"
    );
    std::fs::remove_dir_all(root).unwrap();
}
#[test]
fn staging_port_becomes_one_loopback_production_listener() {
    let root = std::env::temp_dir().join(format!("omt-runtime-good-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    let store = Store::open(&root).unwrap();
    let data = serde_json::to_vec(
        &json!({"inbounds":[{"listen":"127.0.0.1","port":10818,"protocol":"mixed"}]}),
    )
    .unwrap();
    store.write("candidate.json", &data).unwrap();
    use sha2::{Digest, Sha256};
    let hash = format!("{:x}", Sha256::digest(data));
    let result: serde_json::Value =
        serde_json::from_slice(&candidate(&store, &hash).unwrap()).unwrap();
    assert_eq!(result["inbounds"][0]["port"], 10808);
    std::fs::remove_dir_all(root).unwrap();
}
