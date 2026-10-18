use crate::command::{decode_frame,Engine};
use serde_json::{Value,json};
use std::{fs::{self,File,OpenOptions},io::{Read,Write},os::{fd::AsRawFd,unix::{fs::{MetadataExt,PermissionsExt,OpenOptionsExt,FileTypeExt},net::{UnixListener,UnixStream}}},path::Path,sync::{Arc,atomic::{AtomicUsize,Ordering}},time::Duration};

pub struct Server {listener:UnixListener,_lock:File}
impl Server {
 pub fn bind(directory:&Path)->Result<Self,String>{
  if !directory.exists(){fs::create_dir(directory).map_err(|_|"runtime_unavailable")?;fs::set_permissions(directory,fs::Permissions::from_mode(0o700)).map_err(|_|"runtime_permissions")?;}
  let meta=fs::symlink_metadata(directory).map_err(|_|"runtime_unavailable")?;
  if !meta.is_dir()||meta.uid()!=unsafe{libc::geteuid()}||meta.mode()&0o077!=0{return Err("unsafe_runtime".into());}
  let lock=OpenOptions::new().read(true).write(true).create(true).truncate(false).mode(0o600).custom_flags(libc::O_NOFOLLOW).open(directory.join("service.lock")).map_err(|_|"lock_failed")?;
  // SAFETY: descriptor belongs to live File. Lock remains held for Server lifetime.
  if unsafe{libc::flock(lock.as_raw_fd(),libc::LOCK_EX|libc::LOCK_NB)}!=0{return Err("already_running".into());}
  let path=directory.join("control.sock");
  if let Ok(m)=fs::symlink_metadata(&path){if !m.file_type().is_socket()||m.uid()!=unsafe{libc::geteuid()}{return Err("unsafe_socket".into());}fs::remove_file(&path).map_err(|_|"socket_failed")?;}
  let listener=UnixListener::bind(&path).map_err(|_|"bind_failed")?;
  fs::set_permissions(&path,fs::Permissions::from_mode(0o600)).map_err(|_|"socket_permissions")?;
  Ok(Self{listener,_lock:lock})
 }
 pub fn run(self,engine:Arc<Engine>)->Result<(),String>{
  let active=Arc::new(AtomicUsize::new(0));
  for stream in self.listener.incoming(){
   let Ok(mut stream)=stream else{continue};
   if !same_uid(&stream){continue;}
   if active.fetch_add(1,Ordering::SeqCst)>=8 {active.fetch_sub(1,Ordering::SeqCst);let _=stream.write_all(b"{\"error_code\":\"busy\"}\n");continue;}
   let count=active.clone();let engine=engine.clone();
   std::thread::spawn(move||{let _=handle(&mut stream,&engine);count.fetch_sub(1,Ordering::SeqCst);});
  }Ok(())
 }
}
fn same_uid(stream:&UnixStream)->bool {
 let mut cred:libc::ucred=unsafe{std::mem::zeroed()};let mut size=std::mem::size_of::<libc::ucred>() as libc::socklen_t;
 // SAFETY: output points to correctly sized live ucred and socklen_t.
 unsafe{libc::getsockopt(stream.as_raw_fd(),libc::SOL_SOCKET,libc::SO_PEERCRED,(&mut cred as *mut libc::ucred).cast(),&mut size)==0 && cred.uid==libc::geteuid()}
}
pub fn read_frame(stream:&mut impl Read)->Result<Vec<u8>,String>{
 let mut data=Vec::new();let mut byte=[0];
 loop {match stream.read(&mut byte){Ok(0)=>return if data.is_empty(){Err("empty_frame".into())}else{Ok(data)},Ok(_)=>{if byte[0]==b'\n'{return Ok(data);}data.push(byte[0]);if data.len()>65536{return Err("frame_too_large".into());}},Err(_)=>return Err("read_failed".into())}}
}
fn handle(stream:&mut UnixStream,engine:&Engine)->Result<(),String>{
 stream.set_read_timeout(Some(Duration::from_secs(2))).map_err(|_|"timeout_failed")?;
 stream.set_write_timeout(Some(Duration::from_secs(2))).map_err(|_|"timeout_failed")?;
 let raw=read_frame(stream)?;
 let response=match decode_frame(&raw){Ok(c)=>json!({"outcome":engine.dispatch(c),"snapshot":engine.snapshot()}),Err(e)=>json!({"error_code":e})};
 serde_json::to_writer(&mut *stream,&response).map_err(|_|"write_failed")?;stream.write_all(b"\n").map_err(|_|"write_failed")?;Ok(())
}
pub fn request(socket:&Path,data:&[u8])->Result<Value,String>{
 decode_frame(data)?;let mut stream=UnixStream::connect(socket).map_err(|_|"service_unavailable")?;
 if !same_uid(&stream){return Err("peer_mismatch".into());}
 stream.set_read_timeout(Some(Duration::from_secs(125))).map_err(|_|"timeout_failed")?;
 stream.set_write_timeout(Some(Duration::from_secs(2))).map_err(|_|"timeout_failed")?;
 stream.write_all(data).and_then(|_|stream.write_all(b"\n")).map_err(|_|"write_failed")?;
 serde_json::from_slice(&read_frame(&mut stream)?).map_err(|_|"invalid_response".into())
}
