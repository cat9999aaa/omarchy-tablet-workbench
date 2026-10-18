use crate::{
    legacy::run_bounded,
    storage::Store,
    transaction::{self, CoreAdapter, Report},
};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    path::{Path, PathBuf},
    time::Duration,
};
pub fn candidate(store: &Store, hash: &str) -> Result<Vec<u8>, String> {
    let bytes = store.read("candidate.json")?.ok_or("candidate_required")?;
    if hash.len() != 64 || format!("{:x}", Sha256::digest(&bytes)) != hash {
        return Err("candidate_hash_conflict".into());
    }
    let mut config: Value = serde_json::from_slice(&bytes).map_err(|_| "invalid_candidate")?;
    let inbounds = config["inbounds"]
        .as_array()
        .ok_or("candidate_listener_invalid")?;
    if inbounds.len() != 1
        || inbounds[0]["listen"] != "127.0.0.1"
        || inbounds[0]["port"] != 10818
        || inbounds[0]["protocol"] != "mixed"
    {
        return Err("candidate_listener_invalid".into());
    }
    config["inbounds"][0]["port"] = Value::from(10808);
    serde_json::to_vec(&config).map_err(|_| "invalid_candidate".into())
}
struct External {
    root: PathBuf,
    helper: PathBuf,
    validation_hash: String,
}
impl External {
    fn call(&self, action: &str, file: &str, seconds: u64) -> bool {
        let argv = vec![
            "/usr/bin/python3".into(),
            self.helper.to_string_lossy().into_owned(),
            action.into(),
            self.root.join(file).to_string_lossy().into_owned(),
        ];
        run_bounded(&argv, b"", Duration::from_secs(seconds), 4096)
            .ok()
            .and_then(|b| serde_json::from_slice::<Value>(&b).ok())
            .is_some_and(|v| v["ok"] == true)
    }
}
impl CoreAdapter for External {
    fn check(&mut self, bytes: &[u8]) -> bool {
        format!("{:x}", Sha256::digest(bytes)) == self.validation_hash
            && self.call("check", "validation.json", 20)
    }
    fn activate(&mut self) -> bool {
        self.call("activate", "active.json", 20)
    }
    fn probe(&mut self) -> bool {
        self.call("probe", "active.json", 28)
    }
    fn restore(&mut self) -> bool {
        self.call("restore", "active.json", 50)
    }
}
pub fn run(root: &Path, expected: u64, hash: &str, recover: bool) -> Result<Report, String> {
    let home = PathBuf::from(std::env::var("HOME").map_err(|_| "home_unavailable")?);
    if root != home.join(".local/state/omt-proxy") {
        return Err("unexpected_store_path".into());
    }
    let mut store = Store::open(root)?;
    let owner: Value =
        serde_json::from_slice(&store.read("owner.json")?.ok_or("native_owner_required")?)
            .map_err(|_| "invalid_owner")?;
    if owner["owner"] != "omt-proxy" {
        return Err("native_owner_required".into());
    }
    let mut adapter = External {
        root: root.to_path_buf(),
        helper: home.join(".local/lib/omt-proxy/owned-core.py"),
        validation_hash: String::new(),
    };
    if recover {
        return Ok(transaction::recover(&mut store, &mut adapter));
    }
    let data = candidate(&store, hash)?;
    store.write("validation.json", &data)?;
    adapter.validation_hash = format!("{:x}", Sha256::digest(&data));
    Ok(transaction::activate(
        &mut store,
        &mut adapter,
        &data,
        expected,
    ))
}
