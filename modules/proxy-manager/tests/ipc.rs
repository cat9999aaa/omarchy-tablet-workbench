use std::{fs,io::Cursor,os::unix::fs::PermissionsExt,path::PathBuf,process::{Child,Command,Stdio},time::{Duration,Instant}};
use omt_proxy::ipc::{Server,request,read_frame};
use serde_json::json;
struct Instance{child:Child,root:PathBuf}
impl Drop for Instance{fn drop(&mut self){let _=self.child.kill();let _=self.child.wait();let _=fs::remove_dir_all(&self.root);}}
fn start()->Instance {
 let root=std::env::temp_dir().join(format!("omt-ipc-{}-{}",std::process::id(),std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));fs::create_dir(&root).unwrap();
 fs::write(root.join("adapter.py"),r#"import json,sys,time
from pathlib import Path
root=Path(sys.argv[1]); p=root/'enabled'
if sys.argv[2]=='observe': print(json.dumps({'proxy_available':p.exists(),'proxy_tun':p.exists(),'policy':{'proxy_enabled':p.exists()},'flight_saved':False,'ownership':True,'locked':False}))
else:
 d=json.load(sys.stdin);time.sleep(.2)
 with (root/'calls').open('a') as f:f.write('call\n')
 if d['action']=='enable':p.touch()
 else:p.unlink(missing_ok=True)
 print(json.dumps({'stage':'submitted'}))
"#).unwrap();
 let child=Command::new(env!("CARGO_BIN_EXE_omt-proxy")).args(["serve",root.join("runtime").to_str().unwrap(),root.join("adapter.py").to_str().unwrap(),root.to_str().unwrap()]).stdout(Stdio::null()).stderr(Stdio::null()).spawn().unwrap();
 let mut i=Instance{child,root};let end=Instant::now()+Duration::from_secs(4);
 while !i.root.join("runtime/control.sock").exists()&&Instant::now()<end {if i.child.try_wait().unwrap().is_some(){break;}std::thread::sleep(Duration::from_millis(20));}
 i
}
#[test] fn two_clients_share_one_controller(){
 let mut i=start();let sock=i.root.join("runtime/control.sock");assert!(sock.exists(),"service must create socket");assert_eq!(fs::metadata(&sock).unwrap().permissions().mode()&0o777,0o600);
 let data=json!({"id":"s","expected_revision":0,"action":"status","confirmed":false});let v=request(&sock,&serde_json::to_vec(&data).unwrap()).unwrap();let rev=v["snapshot"]["revision"].as_u64().unwrap();
 let a=json!({"id":"a","expected_revision":rev,"action":"enable","confirmed":true});let b=json!({"id":"b","expected_revision":rev,"action":"enable","confirmed":true});
 let other=sock.clone();let t=std::thread::spawn(move||request(&other,&serde_json::to_vec(&a).unwrap()).unwrap());std::thread::sleep(Duration::from_millis(60));let second=request(&sock,&serde_json::to_vec(&b).unwrap()).unwrap();let first=t.join().unwrap();
 assert_eq!(first["outcome"]["stage"],"verified");assert_eq!(second["outcome"]["stage"],"busy");assert_eq!(fs::read_to_string(i.root.join("calls")).unwrap().lines().count(),1);assert!(i.child.try_wait().unwrap().is_none());
 // Dropping all clients does not own or stop either controller or proxy intent.
 let state=request(&sock,&serde_json::to_vec(&data).unwrap()).unwrap();assert_eq!(state["snapshot"]["user_enabled"],true);
 i.child.kill().unwrap();i.child.wait().unwrap();i.child=Command::new(env!("CARGO_BIN_EXE_omt-proxy")).args(["serve",i.root.join("runtime").to_str().unwrap(),i.root.join("adapter.py").to_str().unwrap(),i.root.to_str().unwrap()]).stdout(Stdio::null()).stderr(Stdio::null()).spawn().unwrap();
 std::thread::sleep(Duration::from_millis(250));let state=request(&sock,&serde_json::to_vec(&data).unwrap()).unwrap();assert_eq!(state["snapshot"]["user_enabled"],true);
}
#[test] fn frames_and_runtime_are_safe(){assert!(read_frame(&mut Cursor::new(vec![b'x';65537])).is_err());let root=std::env::temp_dir().join(format!("omt-unsafe-{}",std::process::id()));let _=fs::remove_dir_all(&root);fs::create_dir(&root).unwrap();fs::set_permissions(&root,fs::Permissions::from_mode(0o755)).unwrap();assert!(Server::bind(&root).is_err());fs::remove_dir(&root).unwrap();}
