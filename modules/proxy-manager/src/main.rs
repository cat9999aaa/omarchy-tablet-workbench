use std::{io::{self, Read}, time::{SystemTime, UNIX_EPOCH}};
use serde_json::{json, Value};
use omt_proxy::{legacy::read_network, state::normalize};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.get(1).map(String::as_str)==Some("serve") && args.len()==5 {
        let result=(||{
            let server=omt_proxy::ipc::Server::bind(std::path::Path::new(&args[2]))?;
            let driver=std::sync::Arc::new(omt_proxy::legacy::LegacyDriver{adapter:args[3].clone(),tools_root:args[4].clone()});
            server.run(std::sync::Arc::new(omt_proxy::command::Engine::new(driver)))
        })();
        if let Err(e)=result {eprintln!("{}",json!({"error_code":e}));std::process::exit(1);}return;
    }
    if args.get(1).map(String::as_str)==Some("request") && args.len()==3 {
        let mut input=Vec::new();let _=io::stdin().take(65537).read_to_end(&mut input);
        match omt_proxy::ipc::request(std::path::Path::new(&args[2]),&input){Ok(v)=>println!("{}",v),Err(e)=>{println!("{}",json!({"error_code":e}));std::process::exit(1);}}return;
    }
    if args.get(1).map(String::as_str)==Some("watch") && args.len()==3 {
        use std::io::Write;
        let health=std::path::PathBuf::from(std::env::var("HOME").unwrap_or_default()).join(".local/state/pcadmin-network");
        let events=omt_proxy::events::Events::new(&[health.as_path(),std::path::Path::new("/run/pcadmin-network")]);
        loop {
            let command=json!({"id":"watch","action":"status","expected_revision":0,"confirmed":false});
            let response=omt_proxy::ipc::request(std::path::Path::new(&args[2]),&serde_json::to_vec(&command).unwrap()).unwrap_or_else(|e|json!({"error_code":e}));
            if writeln!(io::stdout(),"{}",response).and_then(|_|io::stdout().flush()).is_err(){break;}
            events.wait();
        }return;
    }
    if args.get(1).map(String::as_str)==Some("catalog") && args.len()==3 {
        let mut input=Vec::new();let _=io::stdin().take(8*1024*1024+1).read_to_end(&mut input);
        match omt_proxy::catalog_cli::run(std::path::Path::new(&args[2]),&input){Ok(v)=>println!("{}",v),Err(e)=>{println!("{}",json!({"error_code":e}));std::process::exit(1);}}return;
    }
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
