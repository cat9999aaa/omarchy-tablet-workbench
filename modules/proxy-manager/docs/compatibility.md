# Proxy compatibility boundary

The initial importer targets the device's existing VLESS raw/Reality and WebSocket/TLS profiles. v2rayN's fixed source enum at commit `673283d` maps `ConfigType=5` to VLESS: https://github.com/2dust/v2rayN/blob/673283d/v2rayN/ServiceLib/Enums/EConfigType.cs . Migration reads SQLite in read-only mode; it never rewrites the original database.

| Capability | Import / validation | Runtime acceptance |
| --- | --- | --- |
| VLESS TCP + Reality + vision | Explicit supported fields; public key and TLS name required; explicit or core-default fingerprint | Pending core and live candidate tests |
| VLESS WebSocket + TLS | Host/path/SNI/ALPN retained; certificate validation required | Pending core and live candidate tests |
| Plaintext VLESS, insecure TLS | Rejected | Not supported |
| VMess, Shadowsocks, Trojan, Hysteria, TUIC and custom outbounds | Explicit unsupported result | Retain old client |
| gRPC, HTTP obfuscation, multiplexing, ECH, custom certificates, extra unknown fields | Rejected; no silent downgrade | Retain old client |
| URI list / base64 URI subscription | Bounded size and strict parsing | Import does not activate anything |

Only node IDs, labels, protocol and capability state cross the public catalog boundary. Endpoint, credential, subscription URL and TLS parameters remain in private files (directory 0700, files 0600). TLS name fallback uses the domain already explicitly supplied in the URI; IP endpoints require a TLS name. A subscription cannot remove LAN/ZeroTier transport protection. New formats require fixtures and a separately updated matrix before being enabled.

This matrix describes the implemented parser boundary; it does not claim every external service or core release was tested. Actual core version evidence belongs in the validation report.

An omitted fingerprint is preserved. The installed Xray 26.10.10 `GetFingerprint("")` selects Chrome Auto, confirmed by a local `run -test` with a fictional Reality profile. See https://github.com/XTLS/Xray-core/blob/v26.10.10/transport/internet/tls/tls.go . This is a documented core default, not disabled TLS verification.
