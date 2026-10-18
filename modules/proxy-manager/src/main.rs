use std::{io::{self, Read}, time::{SystemTime, UNIX_EPOCH}};
use serde_json::{json, Value};
use omt_proxy::{legacy::read_network, state::normalize};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs();
    let raw: Result<Value, String> = match args.get(1).map(String::as_str) {
        Some("snapshot") if args.len() == 3 => read_network(&args[2], now),
        Some("normalize") if args.len() == 2 => {
            let mut data = Vec::new();
            let result = io::stdin().take(262145).read_to_end(&mut data);
            if result.is_err() || data.len() > 262144 { Err("input_too_large".into()) }
            else { serde_json::from_slice(&data).map_err(|_| "invalid_json".into()) }
        }
        _ => { eprintln!("usage: omt-proxy snapshot NETWORK_HELPER | normalize < SNAPSHOT_JSON"); std::process::exit(2); }
    };
    match raw {
        Ok(raw) => println!("{}", serde_json::to_string(&normalize(raw, now)).unwrap()),
        Err(reason) => { println!("{}", json!({"ok":false,"error_code":reason,"snapshot":normalize(json!({}),now)})); std::process::exit(1); }
    }
}
