use crate::{
    catalog::Node,
    routing::{Candidate, Mode},
};
use serde_json::{Value, json};
pub fn build_xray(
    node: &Node,
    candidate: &Candidate,
    template: &Value,
    port: u16,
) -> Result<Value, String> {
    if port == 0 || !candidate.bypass_lan || !candidate.bypass_zerotier {
        return Err("invalid_core_candidate".into());
    }
    let mut node = node.clone();
    let id = node.id.clone();
    node.validate()?;
    if id != node.id || candidate.node_id != node.id {
        return Err("node_integrity_failed".into());
    }
    let mut stream =
        json!({"network":if node.transport=="tcp"{"raw"}else{"ws"},"security":node.security});
    if node.security == "reality" {
        stream["realitySettings"] = json!({"fingerprint":node.fingerprint,"serverName":node.sni,"publicKey":node.public_key,"shortId":node.short_id,"spiderX":node.spider_x});
    } else {
        stream["tlsSettings"] =
            json!({"serverName":node.sni,"fingerprint":node.fingerprint,"allowInsecure":false});
        if !node.alpn.is_empty() {
            stream["tlsSettings"]["alpn"] = json!(node.alpn);
        }
    }
    if node.transport == "ws" {
        stream["wsSettings"] = json!({"path":node.path,"headers":{"Host":if node.host.is_empty(){node.sni.clone()}else{node.host}}});
    }
    let outbound = json!({"tag":"proxy","protocol":"vless","settings":{"address":node.server,"port":node.port,"id":node.credential,"encryption":"none","flow":node.flow},"streamSettings":stream});
    let mut rules = vec![
        json!({"type":"field","ip":["127.0.0.0/8","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","169.254.0.0/16","::1/128","fc00::/7","fe80::/10"],"outboundTag":"direct"}),
    ];
    let dns_tag = template["dns"]["tag"].as_str().filter(|s| !s.is_empty());
    let previous = template["routing"]["rules"].as_array();
    let is_dns = |r: &Value| {
        dns_tag.is_some_and(|tag| {
            r["inboundTag"]
                .as_array()
                .is_some_and(|tags| tags.iter().any(|v| v.as_str() == Some(tag)))
        })
    };
    if let Some(previous) = previous {
        rules.extend(previous.iter().filter(|r| is_dns(r)).cloned());
    }
    if candidate.mode == Mode::Rules {
        for rule in &candidate.rules {
            rules.push(json!({"type":"field","domain":rule.domains,"outboundTag":rule.outbound}));
        }
        if let Some(previous) = previous {
            rules.extend(previous.iter().filter(|r| !is_dns(r)).cloned());
        }
    }
    rules.push(json!({"type":"field","network":"tcp,udp","outboundTag":if candidate.mode==Mode::Direct{"direct"}else{"proxy"}}));
    let mut config = json!({"log":{"loglevel":"warning"},"inbounds":[{"tag":"socks","listen":"127.0.0.1","port":port,"protocol":"mixed","settings":{"udp":true,"auth":"noauth"},"sniffing":{"enabled":true,"destOverride":["http","tls"],"routeOnly":true}}],"outbounds":[outbound,{"tag":"direct","protocol":"freedom"},{"tag":"block","protocol":"blackhole"}],"routing":{"domainStrategy":template["routing"]["domainStrategy"].as_str().unwrap_or("AsIs"),"rules":rules}});
    if template["dns"].is_object() {
        config["dns"] = template["dns"].clone();
    }
    Ok(config)
}
pub fn check_version(version: &str) -> Result<(), String> {
    let parts: Vec<_> = version.split_whitespace().take(2).collect();
    if parts == ["Xray", "26.10.10"] {
        Ok(())
    } else {
        Err("unverified_core_version".into())
    }
}
