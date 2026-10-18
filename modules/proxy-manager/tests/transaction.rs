use omt_proxy::transaction::*;
use std::collections::BTreeMap;
struct Disk {
    files: BTreeMap<String, Vec<u8>>,
    fail: Option<String>,
}
impl JournalIo for Disk {
    fn read(&self, k: &str) -> Result<Option<Vec<u8>>, String> {
        Ok(self.files.get(k).cloned())
    }
    fn write(&mut self, k: &str, v: &[u8]) -> Result<(), String> {
        if self.fail.as_deref() == Some(k) {
            return Err("disk_full".into());
        }
        self.files.insert(k.into(), v.to_vec());
        Ok(())
    }
}
struct Core {
    valid: bool,
    start: bool,
    healthy: bool,
    restore_ok: bool,
    activations: usize,
    restores: usize,
}
impl CoreAdapter for Core {
    fn check(&mut self, _: &[u8]) -> bool {
        self.valid
    }
    fn activate(&mut self) -> bool {
        self.activations += 1;
        self.start
    }
    fn probe(&mut self) -> bool {
        self.healthy
    }
    fn restore(&mut self) -> bool {
        self.restores += 1;
        self.restore_ok
    }
}
fn fixture() -> (Disk, Core) {
    (
        Disk {
            files: BTreeMap::from([("active.json".into(), b"old".to_vec())]),
            fail: None,
        },
        Core {
            valid: true,
            start: true,
            healthy: true,
            restore_ok: true,
            activations: 0,
            restores: 0,
        },
    )
}
#[test]
fn invalid_candidate_never_touches_active() {
    let (mut d, mut c) = fixture();
    c.valid = false;
    let r = activate(&mut d, &mut c, b"new", 0);
    assert!(!r.verified);
    assert_eq!(c.activations, 0);
    assert_eq!(d.files["active.json"], b"old");
}
#[test]
fn success_commits_generation_after_health() {
    let (mut d, mut c) = fixture();
    let r = activate(&mut d, &mut c, b"new", 0);
    assert!(r.verified);
    assert_eq!(r.generation, 1);
    assert_eq!(d.files["active.json"], b"new");
    assert_eq!(d.files["previous.json"], b"old");
    let j: serde_json::Value = serde_json::from_slice(&d.files["transaction.json"]).unwrap();
    assert_eq!(j["stage"], "committed");
}
#[test]
fn startup_and_health_failure_restore_previous() {
    for startup in [true, false] {
        let (mut d, mut c) = fixture();
        c.start = startup;
        c.healthy = false;
        let r = activate(&mut d, &mut c, b"new", 0);
        assert!(!r.verified);
        assert!(r.restored);
        assert_eq!(d.files["active.json"], b"old");
        assert_eq!(c.restores, 1);
    }
}
#[test]
fn disk_failure_never_claims_applied() {
    for name in [
        "previous.json",
        "candidate.json",
        "transaction.json",
        "active.json",
    ] {
        let (mut d, mut c) = fixture();
        d.fail = Some(name.into());
        let r = activate(&mut d, &mut c, b"new", 0);
        assert!(!r.verified);
        assert_eq!(d.files["active.json"], b"old");
    }
}
#[test]
fn restore_failure_is_explicit() {
    let (mut d, mut c) = fixture();
    c.start = false;
    c.restore_ok = false;
    let r = activate(&mut d, &mut c, b"new", 0);
    assert!(!r.verified && !r.restored);
    assert_eq!(r.error_code.as_deref(), Some("restore_failed"));
}
#[test]
fn stale_generation_rejected() {
    let (mut d, mut c) = fixture();
    let r = activate(&mut d, &mut c, b"new", 5);
    assert_eq!(r.error_code.as_deref(), Some("generation_conflict"));
    assert_eq!(c.activations, 0);
}
#[test]
fn crash_during_activation_recovers_on_restart() {
    let (mut d, mut c) = fixture();
    seed_pending(&mut d, b"old", b"new", 7).unwrap();
    d.files.insert("active.json".into(), b"new".to_vec());
    let r = recover(&mut d, &mut c);
    assert!(r.restored);
    assert!(!r.verified);
    assert_eq!(r.generation, 7);
    assert_eq!(d.files["active.json"], b"old");
}
#[test]
fn partial_journal_or_corrupt_backup_is_not_success() {
    let (mut d, mut c) = fixture();
    d.files
        .insert("transaction.json".into(), b"{\"stage\":".to_vec());
    assert!(!recover(&mut d, &mut c).verified);
    let (mut d, mut c) = fixture();
    seed_pending(&mut d, b"old", b"new", 1).unwrap();
    d.files.insert("previous.json".into(), b"corrupt".to_vec());
    let r = recover(&mut d, &mut c);
    assert!(!r.restored);
    assert_eq!(c.restores, 0);
}
#[test]
fn commit_record_failure_rolls_back_live_candidate() {
    struct FailCommit {
        disk: Disk,
        writes: usize,
    }
    impl JournalIo for FailCommit {
        fn read(&self, k: &str) -> Result<Option<Vec<u8>>, String> {
            self.disk.read(k)
        }
        fn write(&mut self, k: &str, v: &[u8]) -> Result<(), String> {
            if k == "transaction.json" {
                self.writes += 1;
                if self.writes == 4 {
                    return Err("disk_full".into());
                }
            }
            self.disk.write(k, v)
        }
    }
    let (d, mut c) = fixture();
    let mut d = FailCommit { disk: d, writes: 0 };
    let r = activate(&mut d, &mut c, b"new", 0);
    assert!(!r.verified);
    assert!(r.restored);
    assert_eq!(d.disk.files["active.json"], b"old");
}
