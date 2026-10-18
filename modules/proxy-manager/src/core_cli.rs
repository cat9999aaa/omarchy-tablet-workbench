use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::Path;
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    mode: crate::routing::Mode,
    node_id: String,
    base_revision: u64,
    rules: Vec<crate::routing::Rule>,
    port: u16,
}
pub fn preview(root: &Path, bytes: &[u8]) -> Result<Value, String> {
    if bytes.len() > 1024 * 1024 {
        return Err("input_too_large".into());
    }
    let r: Request = serde_json::from_slice(bytes).map_err(|_| "invalid_core_request")?;
    // Preview is always a side-port candidate; the running listener cannot be replaced here.
    if r.port != 10818 {
        return Err("candidate_port_required".into());
    }
    let store = crate::storage::Store::open(root)?;
    let catalog = store.catalog()?;
    if catalog.revision != r.base_revision {
        return Err("catalog_revision_conflict".into());
    }
    let node = catalog
        .nodes
        .iter()
        .find(|n| n.id == r.node_id)
        .ok_or("unknown_node")?;
    let draft = crate::routing::RoutingDraft {
        mode: r.mode,
        node_id: r.node_id,
        base_revision: r.base_revision,
        rules: r.rules,
    };
    let c = crate::routing::validate_draft(
        &draft,
        &crate::routing::Capabilities {
            tun: true,
            zerotier_bypass: true,
        },
    )?;
    let template: Value =
        serde_json::from_slice(&store.read("template.json")?.ok_or("template_required")?)
            .map_err(|_| "invalid_template")?;
    let config = crate::core::build_xray(node, &c, &template, r.port)?;
    let data = serde_json::to_vec(&config).map_err(|_| "invalid_core_candidate")?;
    store.write("candidate.json", &data)?;
    store.write("candidate-meta.json",&serde_json::to_vec(&json!({"candidate_hash":format!("{:x}",Sha256::digest(&data)),"node_id":draft.node_id,"mode":draft.mode})).map_err(|_|"invalid_metadata")?)?;
    Ok(
        json!({"candidate_hash":format!("{:x}",Sha256::digest(&data)),"catalog_revision":catalog.revision,"applied":false,"native_checked":false}),
    )
}
