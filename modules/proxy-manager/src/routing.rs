use serde::{Deserialize, Serialize};
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Rules,
    Global,
    Direct,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Rule {
    pub domains: Vec<String>,
    pub outbound: String,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RoutingDraft {
    pub mode: Mode,
    pub node_id: String,
    pub base_revision: u64,
    pub rules: Vec<Rule>,
}
pub struct Capabilities {
    pub tun: bool,
    pub zerotier_bypass: bool,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Candidate {
    pub bypass_lan: bool,
    pub bypass_zerotier: bool,
    pub base_revision: u64,
    pub node_id: String,
    pub mode: Mode,
    pub rules: Vec<Rule>,
}
pub fn validate_draft(d: &RoutingDraft, c: &Capabilities) -> Result<Candidate, String> {
    if !c.tun || !c.zerotier_bypass {
        return Err("transport_protection_required".into());
    }
    if d.node_id.is_empty() || d.node_id.len() > 64 || d.rules.len() > 1024 {
        return Err("invalid_draft".into());
    }
    for rule in &d.rules {
        if !["proxy", "direct", "block"].contains(&rule.outbound.as_str())
            || rule.domains.is_empty()
            || rule.domains.len() > 1024
        {
            return Err("invalid_rule".into());
        }
        for domain in &rule.domains {
            let name = domain
                .strip_prefix("domain:")
                .or_else(|| domain.strip_prefix("full:"))
                .ok_or("unsupported_domain_rule")?;
            if name.is_empty()
                || name.len() > 253
                || !name
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'.' || b == b'-')
            {
                return Err("invalid_domain_rule".into());
            }
        }
    }
    Ok(Candidate {
        bypass_lan: true,
        bypass_zerotier: true,
        base_revision: d.base_revision,
        node_id: d.node_id.clone(),
        mode: d.mode.clone(),
        rules: d.rules.clone(),
    })
}
