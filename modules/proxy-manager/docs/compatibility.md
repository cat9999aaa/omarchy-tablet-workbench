# Proxy compatibility boundary

The initial importer targets the device's existing VLESS raw/Reality and WebSocket/TLS profiles. v2rayN's fixed source enum at commit `673283d` maps `ConfigType=5` to VLESS: https://github.com/2dust/v2rayN/blob/673283d/v2rayN/ServiceLib/Enums/EConfigType.cs . Migration reads SQLite in read-only mode; it never rewrites the original database.

| Capability | Import / validation | Runtime acceptance |
| --- | --- | --- |
| VLESS TCP + Reality + vision | Explicit supported fields; public key and TLS name required; explicit or core-default fingerprint | See task5 evidence below |
| VLESS WebSocket + TLS | Host/path/SNI/ALPN retained; certificate validation required | Exact core native check and isolated authenticated TLS transport passed; provider-specific live profile not switched |
| Plaintext VLESS, insecure TLS | Rejected | Not supported |
| VMess, Shadowsocks, Trojan, Hysteria, TUIC and custom outbounds | Explicit unsupported result | Retain old client |
| gRPC, HTTP obfuscation, multiplexing, ECH, custom certificates, extra unknown fields | Rejected; no silent downgrade | Retain old client |
| URI list / base64 URI subscription | Bounded size and strict parsing | Import does not activate anything |

Only node IDs, labels, protocol and capability state cross the public catalog boundary. Endpoint, credential, subscription URL and TLS parameters remain in private files (directory 0700, files 0600). TLS name fallback uses the domain already explicitly supplied in the URI; IP endpoints require a TLS name. A subscription cannot remove LAN/ZeroTier transport protection. New formats require fixtures and a separately updated matrix before being enabled.

This matrix describes the implemented parser boundary; it does not claim every external service or core release was tested. Actual core version evidence belongs in the validation report.

An omitted fingerprint is preserved. The installed Xray 26.10.10 `GetFingerprint("")` selects Chrome Auto, confirmed by a local `run -test` with a fictional Reality profile. See https://github.com/XTLS/Xray-core/blob/v26.10.10/transport/internet/tls/tls.go . This is a documented core default, not disabled TLS verification.

ALPN is not restricted to HTTP labels. Nonempty custom identifiers up to 255 bytes are retained, with bounded list size and control characters rejected by this UI format. See RFC7301 section3.1: https://www.rfc-editor.org/rfc/rfc7301.html#section-3.1 .

Task5 evidence (2026-10-18): exact Xray26.10.10 and sing-box1.14.3 binaries passed an isolated WS/TLS fixture, IPv4/IPv6 forwarding, DNS hosts resolution, LAN access with upstream stopped, actual TUN IPv4/IPv6, fail-closed proxy loss and owned route/link cleanup. UID policy routing used the namespace's mapped UID0; this does not simulate a real ZeroTier peer.

A separately built candidate using the currently selected real node passed native validation and new Google/gstatic204 requests through127.0.0.1:10818. The old10808 listener remained healthy before/after; the original config/database hashes were unchanged. This is side-port acceptance, not production takeover or a four-node reachability claim.

Fixture-only settings trust an ephemeral local CA and allow fixed documentation-address targets on the local VLESS server. They do not enter imported/production configurations. Xray26.10.10 otherwise uses bundled roots and protects server-side private targets by default; see its fixed `transport/internet/tls/config_other.go`, `config.go`, and `proxy/freedom/freedom.go` sources. No certificate verification was disabled.
