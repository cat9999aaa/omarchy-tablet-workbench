// SPDX-License-Identifier: GPL-3.0-only
use pcadmin_device_observer::{InputNotice,Notifier,udev::{UdevMonitor,MonitorError}};
fn main() {
    let stdout=std::io::stdout();
    let mut notifier=Notifier::new(stdout.lock());
    let mut monitor=match UdevMonitor::open() {
        Ok(m)=>m,
        Err(_)=>{let _=notifier.send(InputNotice::Lost);std::process::exit(1);}
    };
    if notifier.send(InputNotice::Ready).ok()!=Some(true) { return; }
    loop {
        let notice=match monitor.wait() {
            Ok(())=>InputNotice::Changed,
            Err(MonitorError::Lost)=>InputNotice::Lost,
            Err(MonitorError::Closed)=>return,
        };
        if notifier.send(notice).ok()!=Some(true) { return; }
    }
}
