use std::{io::{Read, Write}, os::{fd::AsRawFd, unix::process::CommandExt}, process::{Command, Stdio}, thread, time::{Duration, Instant}};
use serde_json::Value;

pub fn run_bounded(args: &[String], input: &[u8], timeout: Duration, limit: usize) -> Result<Vec<u8>, String> {
    if args.is_empty() { return Err("invalid_command".into()); }
    if input.len() > 4096 { return Err("input_too_large".into()); }
    let mut child = Command::new(&args[0]).args(&args[1..]).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).process_group(0).spawn().map_err(|_| "spawn_failed")?;
    let result = (|| {
        if let Some(mut stdin) = child.stdin.take() { stdin.write_all(input).map_err(|_| "input_failed")?; }
        let mut stdout = child.stdout.take().ok_or("output_failed")?;
        let fd = stdout.as_raw_fd();
        // SAFETY: fd remains owned by stdout throughout these calls.
        unsafe {
            let flags = libc::fcntl(fd, libc::F_GETFL);
            if flags < 0 || libc::fcntl(fd, libc::F_SETFL, flags | libc::O_NONBLOCK) < 0 { return Err("output_failed".into()); }
        }
        let start = Instant::now();
        let mut bytes = Vec::new();
        let mut eof = false;
        let mut status = None;
        loop {
            let mut buffer = [0u8; 4096];
            match stdout.read(&mut buffer) {
                Ok(0) => eof = true,
                Ok(n) => { bytes.extend_from_slice(&buffer[..n]); if bytes.len() > limit { return Err("output_too_large".into()); } }
                Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {},
                Err(e) if e.kind() == std::io::ErrorKind::Interrupted => continue,
                Err(_) => return Err("output_failed".into()),
            }
            if status.is_none() { status = child.try_wait().map_err(|_| "wait_failed")?; }
            if let Some(exit) = status {
                if !exit.success() { return Err("child_failed".into()); }
                if eof { return Ok(bytes); }
            }
            if start.elapsed() >= timeout { return Err("timeout".into()); }
            thread::sleep(Duration::from_millis(10));
        }
    })();
    if result.is_err() {
        // SAFETY: process_group(0) makes this child leader of its own group.
        unsafe { libc::kill(-(child.id() as i32), libc::SIGKILL); }
        let _ = child.wait();
    }
    result
}

pub fn read_network(helper: &str, now: u64) -> Result<Value, String> {
    let bytes = run_bounded(&["/usr/bin/python3".into(), helper.into(), "status".into()], b"", Duration::from_secs(12), 262144)?;
    let mut raw: Value = serde_json::from_slice(&bytes).map_err(|_| "invalid_json")?;
    if !raw.is_object() { return Err("invalid_json".into()); }
    raw["observed_at"] = Value::from(now);
    Ok(raw)
}
