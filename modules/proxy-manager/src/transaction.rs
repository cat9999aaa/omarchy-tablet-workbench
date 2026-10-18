use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
pub trait JournalIo {
    fn read(&self, key: &str) -> Result<Option<Vec<u8>>, String>;
    fn write(&mut self, key: &str, data: &[u8]) -> Result<(), String>;
}
pub trait CoreAdapter {
    fn check(&mut self, data: &[u8]) -> bool;
    fn activate(&mut self) -> bool;
    fn probe(&mut self) -> bool;
    fn restore(&mut self) -> bool;
}
#[derive(Serialize)]
pub struct Report {
    pub stage: String,
    pub verified: bool,
    pub restored: bool,
    pub generation: u64,
    pub error_code: Option<String>,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Journal {
    pub stage: String,
    pub generation: u64,
    pub previous_generation: u64,
    pub candidate_hash: String,
    pub previous_hash: String,
    pub restored: bool,
}
fn digest(b: &[u8]) -> String {
    format!("{:x}", Sha256::digest(b))
}
fn failed(code: &str, generation: u64) -> Report {
    Report {
        stage: "failed".into(),
        verified: false,
        restored: false,
        generation,
        error_code: Some(code.into()),
    }
}
fn save(io: &mut dyn JournalIo, j: &Journal) -> Result<(), String> {
    io.write(
        "transaction.json",
        &serde_json::to_vec(j).map_err(|_| "invalid_journal")?,
    )
}
fn read(io: &dyn JournalIo) -> Result<Option<Journal>, String> {
    io.read("transaction.json")?
        .map(|b| serde_json::from_slice(&b).map_err(|_| "invalid_journal".into()))
        .transpose()
}
fn prepare(
    io: &mut dyn JournalIo,
    previous: &[u8],
    candidate: &[u8],
    generation: u64,
    stage: &str,
) -> Result<Journal, String> {
    let next = generation.checked_add(1).ok_or("generation_overflow")?;
    io.write("previous.json", previous)?;
    io.write("candidate.json", candidate)?;
    let j = Journal {
        stage: stage.into(),
        generation: next,
        previous_generation: generation,
        candidate_hash: digest(candidate),
        previous_hash: digest(previous),
        restored: false,
    };
    save(io, &j)?;
    Ok(j)
}
pub fn seed_pending(
    io: &mut dyn JournalIo,
    previous: &[u8],
    candidate: &[u8],
    generation: u64,
) -> Result<(), String> {
    prepare(io, previous, candidate, generation, "activating").map(|_| ())
}
fn restore(
    io: &mut dyn JournalIo,
    core: &mut dyn CoreAdapter,
    mut j: Journal,
    reason: &str,
) -> Report {
    j.stage = "restoring".into();
    let _ = save(io, &j);
    let previous = match io.read("previous.json") {
        Ok(Some(b)) if digest(&b) == j.previous_hash => b,
        _ => return failed("restore_backup_invalid", j.previous_generation),
    };
    if io.write("active.json", &previous).is_err() || !core.restore() {
        return failed("restore_failed", j.previous_generation);
    }
    j.stage = "failed".into();
    j.restored = true;
    j.generation = j.previous_generation;
    if save(io, &j).is_err() {
        return Report {
            stage: "failed".into(),
            verified: false,
            restored: true,
            generation: j.generation,
            error_code: Some("recovery_journal_failed".into()),
        };
    }
    Report {
        stage: "failed".into(),
        verified: false,
        restored: true,
        generation: j.generation,
        error_code: Some(reason.into()),
    }
}
pub fn activate(
    io: &mut dyn JournalIo,
    core: &mut dyn CoreAdapter,
    candidate: &[u8],
    expected: u64,
) -> Report {
    let previous_journal = match read(io) {
        Ok(v) => v,
        Err(_) => return failed("invalid_journal", 0),
    };
    let generation = previous_journal.as_ref().map(|j| j.generation).unwrap_or(0);
    if previous_journal
        .as_ref()
        .is_some_and(|j| j.stage != "committed" && !(j.stage == "failed" && j.restored))
    {
        return failed("pending_recovery", generation);
    }
    if expected != generation {
        return failed("generation_conflict", generation);
    }
    if candidate.is_empty() || candidate.len() > 8 * 1024 * 1024 || !core.check(candidate) {
        return failed("validation_failed", generation);
    }
    let previous = match io.read("active.json") {
        Ok(Some(b)) => b,
        _ => return failed("previous_config_required", generation),
    };
    let mut j = match prepare(io, &previous, candidate, generation, "prepared") {
        Ok(j) => j,
        Err(_) => return failed("prepare_write_failed", generation),
    };
    j.stage = "validated".into();
    if save(io, &j).is_err() {
        return failed("journal_write_failed", generation);
    }
    j.stage = "activating".into();
    if save(io, &j).is_err() {
        return failed("journal_write_failed", generation);
    }
    if io.write("active.json", candidate).is_err() {
        return restore(io, core, j, "active_write_failed");
    }
    if !core.activate() {
        return restore(io, core, j, "core_start_failed");
    }
    if !core.probe() {
        return restore(io, core, j, "health_failed");
    }
    j.stage = "committed".into();
    if save(io, &j).is_err() {
        return restore(io, core, j, "commit_write_failed");
    }
    Report {
        stage: "committed".into(),
        verified: true,
        restored: false,
        generation: j.generation,
        error_code: None,
    }
}
pub fn recover(io: &mut dyn JournalIo, core: &mut dyn CoreAdapter) -> Report {
    match read(io) {
        Err(_) => failed("invalid_journal", 0),
        Ok(None) => failed("no_transaction", 0),
        Ok(Some(j)) if j.stage == "committed" => Report {
            stage: "committed".into(),
            verified: false,
            restored: false,
            generation: j.generation,
            error_code: None,
        },
        Ok(Some(j)) if j.stage == "failed" && j.restored => Report {
            stage: "failed".into(),
            verified: false,
            restored: true,
            generation: j.generation,
            error_code: None,
        },
        Ok(Some(j)) => restore(io, core, j, "interrupted_activation"),
    }
}
impl JournalIo for crate::storage::Store {
    fn read(&self, key: &str) -> Result<Option<Vec<u8>>, String> {
        crate::storage::Store::read(self, key)
    }
    fn write(&mut self, key: &str, data: &[u8]) -> Result<(), String> {
        crate::storage::Store::write(self, key, data)
    }
}

/// A stale watchdog must never undo a newer operation. Called under Store's lock.
pub fn recover_exact(
    io: &mut dyn JournalIo,
    core: &mut dyn CoreAdapter,
    generation: u64,
    hash: &str,
) -> Report {
    match read(io) {
        Ok(Some(j)) if j.generation == generation && j.candidate_hash == hash => recover(io, core),
        _ => failed("recovery_identity_conflict", generation),
    }
}
