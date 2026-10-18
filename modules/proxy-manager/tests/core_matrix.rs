use omt_proxy::{catalog::*, core::*, routing::*};
use serde_json::json;
fn node() -> Node {
    import_preview(b"vless://11111111-2222-3333-4444-555555555555@proxy.example:443?security=tls&type=ws&path=%2Fws#Fixture",ImportFormat::Uri).unwrap().nodes.remove(0)
}
fn candidate(mode: Mode) -> Candidate {
    validate_draft(
        &RoutingDraft {
            mode,
            node_id: node().id,
            base_revision: 1,
            rules: vec![],
        },
        &Capabilities {
            tun: true,
            zerotier_bypass: true,
        },
    )
    .unwrap()
}
#[test]
fn builder_preserves_rules_and_uses_one_loopback_listener() {
    let n = node();
    let c=build_xray(&n,&candidate(Mode::Rules),&json!({"dns":{"servers":["localhost"]},"routing":{"rules":[{"type":"field","domain":["domain:example.cn"],"outboundTag":"direct"}]}}),10818).unwrap();
    assert_eq!(c["inbounds"].as_array().unwrap().len(), 1);
    assert_eq!(c["inbounds"][0]["listen"], "127.0.0.1");
    assert_eq!(c["inbounds"][0]["port"], 10818);
    assert!(c["routing"].to_string().contains("domain:example.cn"));
    assert_eq!(
        c["outbounds"][0]["streamSettings"]["tlsSettings"]["allowInsecure"],
        false
    );
    assert!(c.get("metrics").is_none());
}
#[test]
fn all_modes_keep_lan_protection() {
    for mode in [Mode::Rules, Mode::Global, Mode::Direct] {
        let c = build_xray(&node(), &candidate(mode), &json!({}), 10818).unwrap();
        let rules = c["routing"]["rules"].as_array().unwrap();
        assert!(rules.iter().any(|r| {
            r["ip"]
                .as_array()
                .is_some_and(|a| a.iter().any(|s| s == "192.168.0.0/16"))
        }));
    }
}
#[test]
fn unsupported_core_version_and_invalid_port_rejected() {
    assert!(check_version("Xray 26.10.10 (Xray)").is_ok());
    assert!(check_version("Xray 99.0.0").is_err());
    assert!(build_xray(&node(), &candidate(Mode::Rules), &json!({}), 0).is_err());
}
#[test]
fn global_keeps_dns_bootstrap_but_not_business_rules() {
    let template = json!({"dns":{"tag":"dns-query","servers":["localhost"]},"routing":{"rules":[{"type":"field","inboundTag":["dns-query"],"outboundTag":"proxy"},{"type":"field","domain":["domain:example.cn"],"outboundTag":"direct"}]}});
    let c = build_xray(&node(), &candidate(Mode::Global), &template, 10818).unwrap();
    let rules = c["routing"]["rules"].to_string();
    assert!(rules.contains("dns-query"));
    assert!(!rules.contains("example.cn"));
}
