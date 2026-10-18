use crate::model::{Field, Freshness, Snapshot};
use serde_json::Value;

fn timestamp(v: &Value) -> Option<u64> {
    v.as_f64()
        .filter(|n| n.is_finite() && *n > 0.0 && *n < u64::MAX as f64)
        .map(|n| n as u64)
}

fn observed<T>(value: Option<T>, at: Option<u64>, now: u64) -> Field<T> {
    let health = match at {
        Some(t) if t <= now && now - t > 45 => Freshness::Stale,
        Some(t) if t <= now && value.is_some() => Freshness::Observed,
        _ => Freshness::Unknown,
    };
    let value = if health == Freshness::Observed {
        value
    } else {
        None
    };
    Field {
        value,
        observed_at: at,
        health,
    }
}

pub fn normalize(raw: Value, now: u64) -> Snapshot {
    let at = timestamp(&raw["observed_at"]);
    let physical = raw["primary"]
        .as_str()
        .filter(|s| ["4g", "wifi", "ethernet", "none"].contains(s))
        .map(str::to_owned);
    let checks = [
        &raw["health"]["internet"],
        &raw["health"]["proxy"],
        &raw["health"]["tun"],
    ];
    let health = if checks.iter().all(|v| v.as_str() == Some("ok")) {
        Some("ok".to_string())
    } else if checks
        .iter()
        .any(|v| v.as_str() == Some("failed") || v.as_str() == Some("unavailable"))
    {
        Some("failed".to_string())
    } else {
        None
    };
    let fresh = at.is_some_and(|t| t <= now && now - t <= 45);
    Snapshot {
        schema: 1,
        revision: 0,
        observed_at: now,
        physical: observed(physical, at, now),
        proxy: observed(raw["proxy_available"].as_bool(), at, now),
        tun: observed(raw["proxy_tun"].as_bool(), at, now),
        health: observed(health, timestamp(&raw["health"]["observed_at"]), now),
        user_enabled: if fresh {
            raw["policy"]["proxy_enabled"].as_bool()
        } else {
            None
        },
        flight: if fresh {
            raw["flight_saved"].as_bool()
        } else {
            None
        },
        capabilities: vec!["status".into()],
    }
}
