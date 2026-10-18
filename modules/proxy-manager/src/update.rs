use serde::{Deserialize, Serialize};
#[derive(Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Application,
    Core,
    Rules,
    Subscription,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct UpdateProposal {
    pub kind: Kind,
    pub source: String,
    pub version: String,
    pub digest: Option<String>,
    pub observed_digest: Option<String>,
    pub prerelease: bool,
    pub observed_at: u64,
    pub compatibility: String,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NetworkPolicy {
    pub flight: Option<bool>,
    pub metered: Option<bool>,
    pub user_enabled: Option<bool>,
    pub now: u64,
}
#[derive(Serialize)]
pub struct Decision {
    pub status: String,
    pub reason: String,
    pub apply: bool,
    pub enable_proxy: bool,
    pub source_authenticated: bool,
    pub verification: String,
    pub install_channel: String,
}
pub fn plan_update(p: &UpdateProposal, n: &NetworkPolicy) -> Decision {
    let channel = match p.kind {
        Kind::Core => "omarchy_then_arch",
        Kind::Rules => "validated_transaction",
        Kind::Application => "reviewed_release",
        Kind::Subscription => "private_catalog_preview",
    };
    let make = |status: &str, reason: &str, verification: &str| Decision {
        status: status.into(),
        reason: reason.into(),
        apply: false,
        enable_proxy: false,
        source_authenticated: false,
        verification: verification.into(),
        install_channel: channel.into(),
    };
    if n.flight != Some(false) {
        return make("paused", "flight_or_unknown", "unverified");
    }
    if n.metered != Some(false) {
        return make("deferred", "metered_or_unknown", "unverified");
    }
    let allowed = match p.kind {
        Kind::Application => p.source == "https://github.com/cat9999aaa/omarchy-tablet-workbench",
        Kind::Core => [
            "https://github.com/XTLS/Xray-core",
            "https://github.com/SagerNet/sing-box",
        ]
        .contains(&p.source.as_str()),
        Kind::Rules => p.source == "https://github.com/Loyalsoldier/v2ray-rules-dat",
        Kind::Subscription => p.source == "local-subscription",
    };
    if !allowed {
        return make("rejected", "source_not_allowed", "unverified");
    }
    if p.observed_at > n.now || n.now - p.observed_at > 86400 {
        return make("rejected", "stale_or_future_metadata", "unverified");
    }
    let version = p.version.to_ascii_lowercase();
    if p.prerelease
        || p.version.is_empty()
        || p.version.len() > 80
        || !p
            .version
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"._+-".contains(&b))
        || ["-rc", "beta", "alpha", "nightly", "preview"]
            .iter()
            .any(|s| version.contains(s))
    {
        return make("rejected", "unstable_version", "unverified");
    }
    for d in [&p.digest, &p.observed_digest].into_iter().flatten() {
        if d.len() != 64 || !d.bytes().all(|b| b.is_ascii_hexdigit()) {
            return make("rejected", "invalid_digest", "unverified");
        }
    }
    if let Some(observed) = &p.observed_digest {
        if p.digest
            .as_ref()
            .is_none_or(|d| !d.eq_ignore_ascii_case(observed))
        {
            return make("rejected", "digest_mismatch", "unverified");
        }
    }
    make(
        "review",
        if p.kind == Kind::Core {
            "use_distribution_channel"
        } else {
            "explicit_review_required"
        },
        if p.observed_digest.is_some() {
            "digest_only"
        } else {
            "not_downloaded"
        },
    )
}
