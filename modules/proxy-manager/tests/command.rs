use omt_proxy::command::*;
use omt_proxy::state::normalize;
use serde_json::json;
use std::sync::{
    Arc, Mutex,
    atomic::{AtomicUsize, Ordering},
};
use std::time::Duration;
struct Mock {
    calls: AtomicUsize,
    state: Mutex<Observation>,
    result: Mutex<String>,
    delay: bool,
}
impl Driver for Mock {
    fn apply_candidate(&self, _: &str) -> String {
        self.calls.fetch_add(1, Ordering::SeqCst);
        "submitted".into()
    }
    fn observe(&self) -> Observation {
        self.state.lock().unwrap().clone()
    }
    fn apply(&self, enabled: bool, _: bool) -> String {
        self.calls.fetch_add(1, Ordering::SeqCst);
        if self.delay {
            std::thread::sleep(Duration::from_millis(150));
        }
        let result = self.result.lock().unwrap().clone();
        if result == "submitted" {
            let mut o = self.state.lock().unwrap();
            o.snapshot.proxy.value = Some(enabled);
            o.snapshot.tun.value = Some(enabled);
            o.snapshot.user_enabled = Some(enabled);
        }
        result
    }
}
fn fixture(delay: bool) -> (Arc<Mock>, Engine) {
    let d = Arc::new(Mock {
        calls: AtomicUsize::new(0),
        state: Mutex::new(Observation {
            snapshot: normalize(
                json!({"observed_at":100,"primary":"4g","proxy_available":false,"proxy_tun":false,"policy":{"proxy_enabled":false},"flight_saved":false}),
                100,
            ),
            locked: Some(false),
            ownership: true,
        }),
        result: Mutex::new("submitted".into()),
        delay,
    });
    let e = Engine::new(d.clone());
    (d, e)
}
fn cmd(id: &str, action: Action, rev: u64) -> Command {
    Command {
        id: id.into(),
        expected_revision: rev,
        action,
        confirmed: true,
        candidate_hash: None,
    }
}
#[test]
fn idempotent_retries_and_conflicting_reuse() {
    let (d, e) = fixture(false);
    let c = cmd("one", Action::Enable, e.snapshot().revision);
    assert_eq!(e.dispatch(c.clone()).stage, "verified");
    assert_eq!(e.dispatch(c).stage, "verified");
    assert_eq!(d.calls.load(Ordering::SeqCst), 1);
    assert_eq!(
        e.dispatch(cmd("one", Action::Disable, e.snapshot().revision))
            .error_code
            .as_deref(),
        Some("id_conflict")
    );
}
#[test]
fn old_revision_rejected() {
    let (d, e) = fixture(false);
    assert_eq!(
        e.dispatch(cmd("old", Action::Enable, 0))
            .error_code
            .as_deref(),
        Some("revision_conflict")
    );
    assert_eq!(d.calls.load(Ordering::SeqCst), 0);
}
#[test]
fn locked_unknown_and_flight_block() {
    for (locked, flight) in [(Some(true), false), (None, false), (Some(false), true)] {
        let (d, e) = fixture(false);
        {
            let mut o = d.state.lock().unwrap();
            o.locked = locked;
            o.snapshot.flight = Some(flight);
        }
        let out = e.dispatch(cmd("gate", Action::Enable, e.snapshot().revision));
        assert_eq!(
            out.error_code.as_deref(),
            Some(if locked != Some(false) {
                "locked_or_unknown"
            } else {
                "flight_or_unknown"
            })
        );
        assert_eq!(d.calls.load(Ordering::SeqCst), 0);
    }
}
#[test]
fn foreign_owner_never_touched() {
    let (d, e) = fixture(false);
    d.state.lock().unwrap().ownership = false;
    assert_eq!(
        e.dispatch(cmd("foreign", Action::Enable, e.snapshot().revision))
            .error_code
            .as_deref(),
        Some("ownership_conflict")
    );
    assert_eq!(d.calls.load(Ordering::SeqCst), 0);
}
#[test]
fn cancellation_timeout_are_not_success() {
    for result in ["cancelled", "timeout"] {
        let (d, e) = fixture(false);
        *d.result.lock().unwrap() = result.into();
        let out = e.dispatch(cmd("cancel", Action::Enable, e.snapshot().revision));
        assert!(!out.verified);
        assert!(out.stage == "cancelled" || out.stage == "failed");
    }
}
#[test]
fn concurrent_busy() {
    let (d, e) = fixture(true);
    let e = Arc::new(e);
    let revision = e.snapshot().revision;
    let other = e.clone();
    let t = std::thread::spawn(move || other.dispatch(cmd("first", Action::Enable, revision)));
    let until = std::time::Instant::now() + Duration::from_secs(2);
    while d.calls.load(Ordering::SeqCst) == 0 && std::time::Instant::now() < until {
        std::thread::yield_now();
    }
    assert_eq!(d.calls.load(Ordering::SeqCst), 1);
    assert_eq!(
        e.dispatch(cmd("second", Action::Enable, revision)).stage,
        "busy"
    );
    assert!(t.join().unwrap().verified);
    assert_eq!(d.calls.load(Ordering::SeqCst), 1);
}
#[test]
fn manual_off_survives_refresh_and_restart() {
    let (d, e) = fixture(false);
    assert!(
        e.dispatch(cmd("off", Action::Disable, e.snapshot().revision))
            .verified
    );
    e.refresh();
    assert_eq!(e.snapshot().user_enabled, Some(false));
    assert_eq!(Engine::new(d.clone()).snapshot().user_enabled, Some(false));
    assert_eq!(d.calls.load(Ordering::SeqCst), 1);
}
#[test]
fn frames_are_bounded_and_strict() {
    assert!(decode_frame(&vec![b'x'; 65537]).is_err());
    assert!(decode_frame(br#"{"id":"a","expected_revision":1,"action":"enable","confirmed":true,"shell":"oops"}"#).is_err());
    assert!(
        decode_frame(br#"{"id":"a","expected_revision":1,"action":"enable","confirmed":true}"#)
            .is_ok()
    );
}

#[test]
fn apply_never_reenables_manual_off() {
    let (d, e) = fixture(false);
    let mut c = cmd("apply-off", Action::Apply, e.snapshot().revision);
    c.candidate_hash = Some("a".repeat(64));
    let result = e.dispatch(c);
    assert_eq!(result.error_code.as_deref(), Some("proxy_not_running"));
    assert_eq!(d.calls.load(Ordering::SeqCst), 0);
}
#[test]
fn apply_requires_hash_confirmation_and_keeps_core_running() {
    let (d, e) = fixture(false);
    assert!(
        e.dispatch(cmd("on", Action::Enable, e.snapshot().revision))
            .verified
    );
    let mut c = cmd("apply-missing", Action::Apply, e.snapshot().revision);
    assert_eq!(
        e.dispatch(c.clone()).error_code.as_deref(),
        Some("candidate_required")
    );
    c.id = "apply-unconfirmed".into();
    c.candidate_hash = Some("a".repeat(64));
    c.confirmed = false;
    assert_eq!(
        e.dispatch(c.clone()).error_code.as_deref(),
        Some("confirmation_required")
    );
    c.id = "apply-now".into();
    c.confirmed = true;
    let out = e.dispatch(c);
    assert!(out.verified);
    assert_eq!(e.snapshot().proxy.value, Some(true));
    assert_eq!(d.calls.load(Ordering::SeqCst), 2);
}
