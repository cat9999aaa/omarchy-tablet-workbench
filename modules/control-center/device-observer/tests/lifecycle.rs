// SPDX-License-Identifier: GPL-3.0-only
use pcadmin_device_observer::{InputNotice, Notifier};
use std::io::{self, BufRead, BufReader, Write};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

#[test]
fn only_fixed_records_with_strict_sequence_and_terminal_loss() {
    let mut bytes = Vec::new();
    {
        let mut n = Notifier::new(&mut bytes);
        assert!(!n.send(InputNotice::Changed).unwrap());
        assert!(n.send(InputNotice::Ready).unwrap());
        assert!(!n.send(InputNotice::Ready).unwrap());
        assert!(n.send(InputNotice::Changed).unwrap());
        assert!(!n.send(InputNotice::Lost).unwrap());
        assert!(!n.send(InputNotice::Changed).unwrap());
    }
    assert_eq!(String::from_utf8(bytes).unwrap(), concat!(
        "{\"schema_version\":1,\"event\":\"ready\",\"seq\":0}\n",
        "{\"schema_version\":1,\"event\":\"changed\",\"seq\":1}\n",
        "{\"schema_version\":1,\"event\":\"lost\",\"seq\":2}\n"));
}
struct Broken;
impl Write for Broken {
    fn write(&mut self, _: &[u8]) -> io::Result<usize> { Err(io::ErrorKind::BrokenPipe.into()) }
    fn flush(&mut self) -> io::Result<()> { Ok(()) }
}
#[test]
fn broken_stdout_is_an_error_not_a_retry() {
    let mut n = Notifier::new(Broken);
    assert_eq!(n.send(InputNotice::Ready).unwrap_err().kind(),io::ErrorKind::BrokenPipe);
}
fn child() -> std::process::Child {
    Command::new(env!("CARGO_BIN_EXE_pcadmin-device-observer")).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap()
}
fn ready(c: &mut std::process::Child) -> BufReader<std::process::ChildStdout> {
    let mut r=BufReader::new(c.stdout.take().unwrap());
    let mut line=String::new(); r.read_line(&mut line).unwrap();
    assert_eq!(line,"{\"schema_version\":1,\"event\":\"ready\",\"seq\":0}\n");r
}
fn wait(c: &mut std::process::Child) {
    let end=Instant::now()+Duration::from_secs(2);
    loop {
        if c.try_wait().unwrap().is_some() { return; }
        if Instant::now()>end { c.kill().unwrap(); c.wait().unwrap(); panic!("observer did not exit"); }
        std::thread::sleep(Duration::from_millis(10));
    }
}
#[test]
fn real_sigterm_and_pipe_close_exit_without_leftover() {
    let mut c=child(); let r=ready(&mut c);
    std::thread::sleep(Duration::from_millis(150));
    assert!(c.try_wait().unwrap().is_none());
    Command::new("kill").args(["-TERM",&c.id().to_string()]).status().unwrap();wait(&mut c);
    assert_eq!(r.lines().count(),0);
    let mut c=child();let r=ready(&mut c);drop(r);wait(&mut c);
}
