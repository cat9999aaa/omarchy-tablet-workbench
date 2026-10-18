use crate::{
    legacy::{read_network, run_bounded},
    storage::Store,
    update::{NetworkPolicy, UpdateProposal, plan_update},
};
use serde_json::{Value, json};
use std::{
    path::{Path, PathBuf},
    time::{Duration, SystemTime, UNIX_EPOCH},
};
pub fn run(root: &Path, input: &[u8]) -> Result<Value, String> {
    if input.len() > 1024 {
        return Err("input_too_large".into());
    }
    let request: Value = serde_json::from_slice(input).map_err(|_| "invalid_request")?;
    if request.as_object().is_none_or(|o| o.len() != 1)
        || !["list", "check"].contains(&request["action"].as_str().unwrap_or(""))
    {
        return Err("invalid_update_action".into());
    }
    let home = PathBuf::from(std::env::var("HOME").map_err(|_| "home_unavailable")?);
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let raw = read_network(
        &home
            .join("Projects/pcadmin/tools/network-center/network.py")
            .to_string_lossy(),
        now,
    )
    .unwrap_or(Value::Null);
    let policy = NetworkPolicy {
        flight: raw["flight_saved"].as_bool(),
        metered: match raw["primary"].as_str() {
            Some("4g") => Some(true),
            Some("wifi" | "ethernet") => Some(false),
            _ => None,
        },
        user_enabled: raw["policy"]["proxy_enabled"].as_bool(),
        now,
    };
    let store = Store::open(root)?;
    if request["action"] == "check" {
        if policy.flight != Some(false) {
            return Err("flight_or_unknown".into());
        }
        if policy.metered != Some(false) {
            return Err("metered_or_unknown".into());
        }
        let script = home.join(".local/lib/omt-proxy/proxy-upstream.py");
        let bytes = run_bounded(
            &[
                "/usr/bin/python3".into(),
                script.to_string_lossy().into_owned(),
                "--online".into(),
            ],
            b"",
            Duration::from_secs(50),
            1024 * 1024,
        )
        .map_err(|_| "update_check_failed")?;
        inspect(&bytes, &policy)?;
        store.write("updates.json", &bytes)?;
    }
    match store.read("updates.json")? {
        Some(bytes) => inspect(&bytes, &policy),
        None => Ok(json!({"observed_at":null,"proposals":[],"checks":[]})),
    }
}
pub fn inspect(bytes: &[u8], policy: &NetworkPolicy) -> Result<Value, String> {
    let v: Value = serde_json::from_slice(bytes).map_err(|_| "invalid_update_metadata")?;
    if v["schema"] != 1 {
        return Err("invalid_update_metadata".into());
    }
    let proposals = v["proposals"].as_array().ok_or("invalid_update_metadata")?;
    if proposals.len() > 16 {
        return Err("invalid_update_metadata".into());
    }
    let mut result = Vec::new();
    for raw in proposals {
        let proposal: UpdateProposal =
            serde_json::from_value(raw.clone()).map_err(|_| "invalid_update_metadata")?;
        let decision = plan_update(&proposal, policy);
        result.push(json!({"proposal":proposal,"decision":decision}));
    }
    let checks: Vec<_> = v["checks"]
        .as_array()
        .into_iter()
        .flatten()
        .take(16)
        .filter_map(|c| {
            let source = c["source"].as_str()?;
            let status = c["status"].as_str()?;
            if ![
                "XTLS/Xray-core",
                "SagerNet/sing-box",
                "Loyalsoldier/v2ray-rules-dat",
                "cat9999aaa/omarchy-tablet-workbench",
            ]
            .contains(&source)
                || !["observed", "no_release", "unavailable"].contains(&status)
            {
                return None;
            }
            Some(json!({"source":source,"status":status}))
        })
        .collect();
    Ok(json!({"observed_at":v["observed_at"].as_u64(),"proposals":result,"checks":checks}))
}
