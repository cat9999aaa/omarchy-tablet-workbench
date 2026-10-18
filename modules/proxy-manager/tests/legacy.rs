use omt_proxy::legacy::run_bounded;
use std::time::{Duration, Instant};

fn python(code: &str) -> Vec<String> {
    vec!["/usr/bin/python3".into(), "-c".into(), code.into()]
}

#[test]
fn reads_only_successful_bounded_output() {
    let result = run_bounded(&python("import sys; print(sys.stdin.read())"), b"hello", Duration::from_secs(2), 100).unwrap();
    assert_eq!(result, b"hello\n");
}

#[test]
fn timeout_terminates_slow_helper() {
    let start = Instant::now();
    let result = run_bounded(&python("import time; time.sleep(3)"), b"", Duration::from_millis(80), 100);
    assert_eq!(result.unwrap_err(), "timeout");
    assert!(start.elapsed() < Duration::from_secs(2));
}

#[test]
fn output_limit_and_child_failure_never_leak_output() {
    assert_eq!(run_bounded(&python("print('x'*1000)"), b"", Duration::from_secs(2), 100).unwrap_err(), "output_too_large");
    assert_eq!(run_bounded(&python("import sys; print('SECRET'); sys.exit(3)"), b"", Duration::from_secs(2), 100).unwrap_err(), "child_failed");
}

#[test]
fn missing_helper_and_invalid_input_are_safe() {
    assert_eq!(run_bounded(&[], b"", Duration::from_secs(1), 100).unwrap_err(), "invalid_command");
    assert_eq!(run_bounded(&python("print('ok')"), &vec![0;65537], Duration::from_secs(1), 100).unwrap_err(), "input_too_large");
}
