use crate::model::Snapshot;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum Action {
    Status,
    Enable,
    Disable,
    Apply,
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Command {
    pub id: String,
    pub expected_revision: u64,
    pub action: Action,
    pub confirmed: bool,
    #[serde(default)]
    pub candidate_hash: Option<String>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Outcome {
    pub id: String,
    pub stage: String,
    pub verified: bool,
    pub error_code: Option<String>,
    pub revision: u64,
}
#[derive(Clone)]
pub struct Observation {
    pub snapshot: Snapshot,
    pub locked: Option<bool>,
    pub ownership: bool,
}
pub trait Driver: Send + Sync {
    fn observe(&self) -> Observation;
    fn apply(&self, enabled: bool, confirmed: bool) -> String;
    fn apply_candidate(&self, _hash: &str) -> String {
        "unsupported".into()
    }
}
struct State {
    observation: Observation,
    recent: std::collections::VecDeque<(Command, Outcome)>,
}
pub struct Engine {
    driver: Arc<dyn Driver>,
    state: std::sync::Mutex<State>,
    operation: std::sync::Mutex<()>,
}
impl Engine {
    pub fn new(driver: Arc<dyn Driver>) -> Self {
        let mut observation = driver.observe();
        observation.snapshot.revision = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_micros() as u64;
        Self {
            driver,
            state: std::sync::Mutex::new(State {
                observation,
                recent: Default::default(),
            }),
            operation: std::sync::Mutex::new(()),
        }
    }
    pub fn snapshot(&self) -> Snapshot {
        self.state.lock().unwrap().observation.snapshot.clone()
    }
    fn record_observation(&self, mut observation: Observation) {
        let mut s = self.state.lock().unwrap();
        observation.snapshot.revision = s.observation.snapshot.revision + 1;
        s.observation = observation;
    }
    pub fn refresh(&self) {
        if let Ok(_guard) = self.operation.try_lock() {
            self.record_observation(self.driver.observe());
        }
    }
    pub fn dispatch(&self, c: Command) -> Outcome {
        let make = |stage: &str, error: Option<&str>, revision: u64| Outcome {
            id: c.id.clone(),
            stage: stage.into(),
            verified: stage == "verified",
            error_code: error.map(str::to_owned),
            revision,
        };
        {
            let s = self.state.lock().unwrap();
            if let Some((old, result)) = s.recent.iter().find(|(old, _)| old.id == c.id) {
                return if old == &c {
                    result.clone()
                } else {
                    make(
                        "conflict",
                        Some("id_conflict"),
                        s.observation.snapshot.revision,
                    )
                };
            }
        }
        let Ok(_guard) = self.operation.try_lock() else {
            return make("busy", Some("busy"), self.snapshot().revision);
        };
        {
            let s = self.state.lock().unwrap();
            if let Some((old, result)) = s.recent.iter().find(|(old, _)| old.id == c.id) {
                return if old == &c {
                    result.clone()
                } else {
                    make(
                        "conflict",
                        Some("id_conflict"),
                        s.observation.snapshot.revision,
                    )
                };
            }
        }
        let revision = self.snapshot().revision;
        if c.action == Action::Status {
            self.record_observation(self.driver.observe());
            return make("verified", None, self.snapshot().revision);
        }
        if c.expected_revision != revision {
            return make("conflict", Some("revision_conflict"), revision);
        }
        // Refresh gates immediately before dispatch; queued GUI state is never authority.
        let observed = self.driver.observe();
        let error = if observed.locked != Some(false) {
            Some("locked_or_unknown")
        } else if !observed.ownership {
            Some("ownership_conflict")
        } else if c.action != Action::Disable && observed.snapshot.flight != Some(false) {
            Some("flight_or_unknown")
        } else if matches!(c.action, Action::Disable | Action::Apply) && !c.confirmed {
            Some("confirmation_required")
        } else if c.action == Action::Apply
            && (observed.snapshot.user_enabled != Some(true)
                || observed.snapshot.proxy.value != Some(true)
                || observed.snapshot.tun.value != Some(true))
        {
            Some("proxy_not_running")
        } else if c.action == Action::Apply
            && !c
                .candidate_hash
                .as_ref()
                .is_some_and(|h| h.len() == 64 && h.bytes().all(|b| b.is_ascii_hexdigit()))
        {
            Some("candidate_required")
        } else {
            None
        };
        if let Some(error) = error {
            return make("conflict", Some(error), revision);
        }
        let enabled = c.action != Action::Disable;
        let result = if c.action == Action::Apply {
            self.driver
                .apply_candidate(c.candidate_hash.as_deref().unwrap())
        } else {
            self.driver.apply(enabled, c.confirmed)
        };
        let after = self.driver.observe();
        let verified = result == "submitted"
            && after.snapshot.proxy.value == Some(enabled)
            && after.snapshot.tun.value == Some(enabled)
            && after.snapshot.user_enabled == Some(enabled);
        self.record_observation(after);
        let out = if verified {
            make("verified", None, self.snapshot().revision)
        } else if result == "cancelled" {
            make(
                "cancelled",
                Some("authorization_cancelled"),
                self.snapshot().revision,
            )
        } else {
            make(
                "failed",
                Some(if result == "timeout" {
                    "timeout"
                } else {
                    "not_verified"
                }),
                self.snapshot().revision,
            )
        };
        let mut s = self.state.lock().unwrap();
        s.recent.push_back((c.clone(), out.clone()));
        while s.recent.len() > 128 {
            s.recent.pop_front();
        }
        out
    }
}
pub fn decode_frame(bytes: &[u8]) -> Result<Command, String> {
    if bytes.len() > 65536 {
        return Err("frame_too_large".into());
    }
    let c: Command = serde_json::from_slice(bytes).map_err(|_| "invalid_request")?;
    if c.id.is_empty()
        || c.id.len() > 64
        || !c
            .id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
    {
        return Err("invalid_id".into());
    }
    Ok(c)
}
