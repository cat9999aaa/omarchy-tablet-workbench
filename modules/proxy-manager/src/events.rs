//! Subscribe to the existing NetworkManager-backed producer. No second network probe loop.
use std::{ffi::CString,os::fd::{FromRawFd,AsRawFd},fs::File,path::Path,time::Duration};
pub struct Events {fd:Option<File>}
impl Events {
 pub fn new(paths:&[&Path])->Self {
  let n=unsafe{libc::inotify_init1(libc::IN_CLOEXEC|libc::IN_NONBLOCK)};
  if n<0{return Self{fd:None};}
  let fd=unsafe{File::from_raw_fd(n)};
  for path in paths {if let Ok(p)=CString::new(path.as_os_str().as_encoded_bytes()){unsafe{libc::inotify_add_watch(n,p.as_ptr(),libc::IN_CLOSE_WRITE|libc::IN_MOVED_TO|libc::IN_DELETE|libc::IN_CREATE)};}}
  Self{fd:Some(fd)}
 }
 pub fn wait(&self) {
  if let Some(fd)=&self.fd {
   let mut p=libc::pollfd{fd:fd.as_raw_fd(),events:libc::POLLIN,revents:0};
   unsafe{libc::poll(&mut p,1,60000)};
   if p.revents!=0 {std::thread::sleep(Duration::from_millis(250));let mut b=[0u8;16384];while unsafe{libc::read(fd.as_raw_fd(),b.as_mut_ptr().cast(),b.len())}>0 {}}
  }else{std::thread::sleep(Duration::from_secs(60));}
 }
}
