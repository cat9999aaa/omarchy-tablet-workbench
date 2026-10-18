use crate::{
    catalog::{ImportFormat, ImportPreview, import_preview},
    legacy::run_bounded,
    storage::{Catalog, Store},
};
use serde_json::{Value, json};
use std::{
    io::Read,
    path::{Path, PathBuf},
    time::Duration,
};
fn public(c: Catalog) -> Value {
    json!({"revision":c.revision,"current":c.current,"nodes":ImportPreview{nodes:c.nodes}.public()})
}
fn string<'a>(v: &'a Value, key: &str) -> Result<&'a str, String> {
    v[key].as_str().ok_or("invalid_request".into())
}
pub fn run(root: &Path, bytes: &[u8]) -> Result<Value, String> {
    if bytes.len() > 8 * 1024 * 1024 {
        return Err("input_too_large".into());
    }
    let v: Value = serde_json::from_slice(bytes).map_err(|_| "invalid_request")?;
    let action = string(&v, "action")?;
    let allowed = match action {
        "list" | "migrate" => vec!["action"],
        "preview-uri" => vec!["action", "text"],
        "preview-file" => vec!["action", "path"],
        "preview-url" => vec!["action", "url", "alias", "confirmed"],
        "commit" => vec!["action", "preview_id", "confirmed"],
        "routing-preview" => vec!["action", "draft"],
        _ => return Err("unsupported_catalog_action".into()),
    };
    if v.as_object()
        .ok_or("invalid_request")?
        .keys()
        .any(|k| !allowed.contains(&k.as_str()))
    {
        return Err("unsupported_field".into());
    }
    let store = Store::open(root)?;
    if action == "list" {
        return Ok(public(store.catalog()?));
    }
    if action == "commit" {
        return Ok(public(store.commit(
            string(&v, "preview_id")?,
            v["confirmed"].as_bool() == Some(true),
        )?));
    }
    if action == "routing-preview" {
        let draft: crate::routing::RoutingDraft =
            serde_json::from_value(v["draft"].clone()).map_err(|_| "invalid_draft")?;
        let catalog = store.catalog()?;
        if draft.base_revision != catalog.revision
            || !catalog.nodes.iter().any(|n| n.id == draft.node_id)
        {
            return Err("catalog_revision_conflict".into());
        }
        let candidate = crate::routing::validate_draft(
            &draft,
            &crate::routing::Capabilities {
                tun: true,
                zerotier_bypass: true,
            },
        )?;
        store.write(
            "routing-draft.json",
            &serde_json::to_vec(&candidate).map_err(|_| "invalid_draft")?,
        )?;
        return Ok(json!({"draft":candidate,"applied":false}));
    }
    let (data, format) = match action {
        "migrate" => {
            let home = std::env::var("HOME").map_err(|_| "home_unavailable")?;
            let path = PathBuf::from(home).join(".local/share/v2rayN/guiConfigs/guiNDB.db");
            let helper = std::env::var("OMT_PROXY_MIGRATOR")
                .map(PathBuf::from)
                .unwrap_or_else(|_| {
                    std::env::current_exe()
                        .unwrap_or_default()
                        .with_file_name("migrate-v2rayn.py")
                });
            let data = run_bounded(
                &[
                    "/usr/bin/python3".into(),
                    helper.to_string_lossy().into_owned(),
                    path.to_string_lossy().into_owned(),
                ],
                b"",
                Duration::from_secs(20),
                8 * 1024 * 1024,
            )
            .map_err(|_| "migration_unsupported")?;
            (data, ImportFormat::LegacyJson)
        }
        "preview-uri" => (string(&v, "text")?.as_bytes().to_vec(), ImportFormat::Uri),
        "preview-file" => {
            let path = string(&v, "path")?;
            let path = if path.starts_with("file:") {
                url::Url::parse(path)
                    .map_err(|_| "invalid_file")?
                    .to_file_path()
                    .map_err(|_| "invalid_file")?
            } else {
                PathBuf::from(path)
            };
            let f = std::fs::File::open(path).map_err(|_| "import_file_unavailable")?;
            if !f
                .metadata()
                .map_err(|_| "import_file_unavailable")?
                .is_file()
            {
                return Err("invalid_import_file".into());
            }
            let mut data = Vec::new();
            f.take(8 * 1024 * 1024 + 1)
                .read_to_end(&mut data)
                .map_err(|_| "import_file_unavailable")?;
            let format = if data.starts_with(b"vless://") {
                ImportFormat::Uri
            } else {
                ImportFormat::Base64
            };
            (data, format)
        }
        "preview-url" => {
            if v["confirmed"].as_bool() != Some(true) {
                return Err("metered_confirmation_required".into());
            }
            if Path::new("/var/lib/pcadmin-network/flight.json").exists() {
                return Err("flight_active".into());
            }
            let url = string(&v, "url")?;
            let alias = string(&v, "alias")?;
            if alias.len() > 80 || alias.chars().any(char::is_control) {
                return Err("invalid_alias".into());
            }
            let data = crate::subscription::download(url)?;
            let format = if data.starts_with(b"vless://") {
                ImportFormat::Uri
            } else {
                ImportFormat::Base64
            };
            let preview = import_preview(&data, format)?;
            store.stage(&preview)?;
            store.write(
                "subscription.json",
                &serde_json::to_vec(&json!({"alias":alias,"url":url}))
                    .map_err(|_| "invalid_subscription")?,
            )?;
            return store.staged_public();
        }
        _ => return Err("unsupported_catalog_action".into()),
    };
    let preview = import_preview(&data, format)?;
    store.stage(&preview)?;
    store.staged_public()
}
