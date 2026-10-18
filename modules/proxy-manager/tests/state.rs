use omt_proxy::state::normalize as normalize_snapshot;
use serde_json::{json, Value};

fn normalize(raw: Value, now: u64) -> Value {
    serde_json::to_value(normalize_snapshot(raw, now)).unwrap()
}

fn sample() -> Value {
    json!({"observed_at":100,"primary":"4g","proxy_available":true,
        "proxy_tun":true,"policy":{"proxy_enabled":true},"flight_saved":false,
        "health":{"observed_at":100,"internet":"ok","proxy":"ok","tun":"ok"}})
}

#[test]
fn stale_never_connected() {
    assert_eq!(normalize(sample(), 145)["health"]["value"], "ok");
    let stale = normalize(sample(), 146);
    assert_eq!(stale["health"]["health"], "stale");
    assert!(stale["health"]["value"].is_null());
}

#[test]
fn future_timestamp_unknown() {
    let value = normalize(sample(), 99);
    assert_eq!(value["health"]["health"], "unknown");
    assert!(value["health"]["value"].is_null());
}

#[test]
fn missing_fields_unknown() {
    let value = normalize(json!({}), 100);
    assert_eq!(value["proxy"]["health"], "unknown");
    assert!(value["user_enabled"].is_null());
    assert!(value["flight"].is_null());
    assert!(value["health"]["value"].is_null());
}

#[test]
fn secret_fields_not_serialized() {
    let mut raw = sample();
    raw["Password"] = json!("SECRET_PASSWORD");
    raw["Url"] = json!("SECRET_SUBSCRIPTION");
    raw["Address"] = json!("SECRET_NODE_ADDRESS");
    raw["primary"] = json!("SECRET_INTERFACE");
    let value = normalize(raw, 100);
    assert_eq!(value["schema"], 1);
    assert!(!value.to_string().contains("SECRET_"));
}

#[test]
fn port_open_is_not_internet_success() {
    let mut raw = sample();
    raw["health"]["tun"] = json!("failed");
    let value = normalize(raw, 100);
    assert_eq!(value["proxy"]["value"], true);
    assert_eq!(value["health"]["value"], "failed");
}

#[test]
fn malformed_values_are_unknown_not_false() {
    let mut raw = sample();
    raw["proxy_available"] = json!("true");
    raw["health"]["observed_at"] = json!(-1);
    let value = normalize(raw, 100);
    assert!(value["proxy"]["value"].is_null());
    assert_eq!(value["health"]["health"], "unknown");
}
