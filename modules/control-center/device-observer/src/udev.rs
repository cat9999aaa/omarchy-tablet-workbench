// SPDX-License-Identifier: GPL-3.0-only
//! Owns only libudev notification objects. Never opens input streams or queries identity.
use std::ffi::{c_char,c_int,c_short,c_void};
use std::io;
use std::ptr;

#[repr(C)]
struct PollFd { fd:c_int, events:c_short, revents:c_short }
#[link(name="udev")]
extern "C" {
    fn udev_new() -> *mut c_void;
    fn udev_unref(p:*mut c_void) -> *mut c_void;
    fn udev_monitor_new_from_netlink(p:*mut c_void,name:*const c_char) -> *mut c_void;
    fn udev_monitor_unref(p:*mut c_void) -> *mut c_void;
    fn udev_monitor_filter_add_match_subsystem_devtype(p:*mut c_void,sub:*const c_char,dev:*const c_char) -> c_int;
    fn udev_monitor_enable_receiving(p:*mut c_void) -> c_int;
    fn udev_monitor_get_fd(p:*mut c_void) -> c_int;
    fn udev_monitor_receive_device(p:*mut c_void) -> *mut c_void;
    fn udev_device_unref(p:*mut c_void) -> *mut c_void;
    fn poll(fds:*mut PollFd,nfds:usize,timeout:c_int) -> c_int;
}
#[derive(Debug,PartialEq)]
pub enum MonitorError { Lost, Closed }
pub struct UdevMonitor { context:*mut c_void, monitor:*mut c_void, fd:c_int }
fn receive_error(error:io::Error) -> Result<(),MonitorError> {
    match error.raw_os_error() { Some(4)|Some(11) => Ok(()), _ => Err(MonitorError::Lost) }
}
impl UdevMonitor {
    pub fn open() -> Result<Self,MonitorError> {
        // All acquired objects are owned by this value, including on early error.
        let mut result=Self { context:ptr::null_mut(), monitor:ptr::null_mut(), fd:-1 };
        unsafe {
            result.context=udev_new();
            if result.context.is_null() { return Err(MonitorError::Lost); }
            result.monitor=udev_monitor_new_from_netlink(result.context,c"udev".as_ptr());
            if result.monitor.is_null() { return Err(MonitorError::Lost); }
            if udev_monitor_filter_add_match_subsystem_devtype(result.monitor,c"input".as_ptr(),ptr::null())<0
                || udev_monitor_enable_receiving(result.monitor)<0 { return Err(MonitorError::Lost); }
            result.fd=udev_monitor_get_fd(result.monitor);
            if result.fd<0 { return Err(MonitorError::Lost); }
        }
        Ok(result)
    }
    pub fn wait(&mut self) -> Result<(),MonitorError> {
        loop {
            // A broken stdout pipe must also wake an otherwise idle observer.
            let mut fds=[PollFd{fd:self.fd,events:1,revents:0},PollFd{fd:1,events:0,revents:0}];
            let n=unsafe { poll(fds.as_mut_ptr(),fds.len(),-1) };
            if n<0 {
                if io::Error::last_os_error().kind()==io::ErrorKind::Interrupted { continue; }
                return Err(MonitorError::Lost);
            }
            if fds[1].revents & (8|16|32) !=0 { return Err(MonitorError::Closed); }
            if fds[0].revents & (8|16|32) !=0 { return Err(MonitorError::Lost); }
            if fds[0].revents & 1 !=0 {
                let device=unsafe { udev_monitor_receive_device(self.monitor) };
                if device.is_null() { receive_error(io::Error::last_os_error())?; continue; }
                unsafe { udev_device_unref(device); }
                return Ok(());
            }
        }
    }
}
impl Drop for UdevMonitor {
    fn drop(&mut self) {
        unsafe {
            if !self.monitor.is_null() { udev_monitor_unref(self.monitor); }
            if !self.context.is_null() { udev_unref(self.context); }
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn enobufs_is_loss_not_change() {
        assert_eq!(receive_error(io::Error::from_raw_os_error(105)),Err(MonitorError::Lost));
        assert_eq!(receive_error(io::Error::from_raw_os_error(4)),Ok(()));
        assert_eq!(receive_error(io::Error::from_raw_os_error(11)),Ok(()));
    }
}
