use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum Freshness { Observed, Stale, Unknown, Unavailable }

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Field<T> {
    pub value: Option<T>,
    pub observed_at: Option<u64>,
    pub health: Freshness,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Snapshot {
    pub schema: u32,
    pub revision: u64,
    pub observed_at: u64,
    pub physical: Field<String>,
    pub proxy: Field<bool>,
    pub tun: Field<bool>,
    pub health: Field<String>,
    pub user_enabled: Option<bool>,
    pub flight: Option<bool>,
    pub capabilities: Vec<String>,
}
