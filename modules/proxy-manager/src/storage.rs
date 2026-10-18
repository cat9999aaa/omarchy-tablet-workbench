use crate::catalog::{ImportPreview, Node, preview_replace};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    os::{
        fd::AsRawFd,
        unix::fs::{MetadataExt, OpenOptionsExt, PermissionsExt},
    },
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Catalog {
    pub revision: u64,
    pub nodes: Vec<Node>,
    pub current: Option<String>,
}
#[derive(Serialize, Deserialize)]
struct Staged {
    base: u64,
    preview: ImportPreview,
}
pub struct Store {
    pub root: PathBuf,
    _lock: File,
}
impl Drop for Store {
    fn drop(&mut self) {
        // An unrelated concurrent spawn may inherit this open-file description until exec.
        // Explicit unlock releases ownership now, rather than waiting for that child close.
        unsafe {
            libc::flock(self._lock.as_raw_fd(), libc::LOCK_UN);
        }
    }
}
impl Store {
    pub fn open(path: &Path) -> Result<Self, String> {
        let root = std::path::absolute(path).map_err(|_| "invalid_store")?;
        let mut cursor = PathBuf::new();
        for part in root.components() {
            cursor.push(part);
            if fs::symlink_metadata(&cursor).is_ok_and(|m| m.file_type().is_symlink()) {
                return Err("unsafe_store_path".into());
            }
        }
        if !root.exists() {
            fs::create_dir_all(&root).map_err(|_| "store_unavailable")?;
            fs::set_permissions(&root, fs::Permissions::from_mode(0o700))
                .map_err(|_| "store_permissions")?;
        }
        let m = fs::symlink_metadata(&root).map_err(|_| "store_unavailable")?;
        if !m.is_dir() || m.uid() != unsafe { libc::geteuid() } || m.mode() & 0o077 != 0 {
            return Err("unsafe_store_permissions".into());
        }
        let lock = OpenOptions::new()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .mode(0o600)
            .custom_flags(libc::O_NOFOLLOW)
            .open(root.join("catalog.lock"))
            .map_err(|_| "store_lock_failed")?;
        if unsafe { libc::flock(lock.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
            return Err("catalog_busy".into());
        }
        Ok(Self { root, _lock: lock })
    }
    pub fn read(&self, name: &str) -> Result<Option<Vec<u8>>, String> {
        if !filename(name) {
            return Err("invalid_store_name".into());
        }
        let file = OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW)
            .open(self.root.join(name));
        let mut file = match file {
            Ok(f) => f,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(_) => return Err("private_read_failed".into()),
        };
        let m = file.metadata().map_err(|_| "private_read_failed")?;
        if !m.is_file()
            || m.uid() != unsafe { libc::geteuid() }
            || m.mode() & 0o077 != 0
            || m.nlink() != 1
            || m.len() > 8 * 1024 * 1024
        {
            return Err("unsafe_private_file".into());
        }
        let mut data = Vec::new();
        Read::by_ref(&mut file)
            .take(8 * 1024 * 1024 + 1)
            .read_to_end(&mut data)
            .map_err(|_| "private_read_failed")?;
        if data.len() > 8 * 1024 * 1024 {
            return Err("private_file_too_large".into());
        }
        Ok(Some(data))
    }
    pub fn write(&self, name: &str, data: &[u8]) -> Result<(), String> {
        if !filename(name) || data.len() > 8 * 1024 * 1024 {
            return Err("invalid_private_write".into());
        }
        // Validate an existing target before atomically replacing it.
        self.read(name)?;
        let tmp = self.root.join(format!(
            ".new-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_nanos()
        ));
        let result = (|| {
            let mut f = OpenOptions::new()
                .create_new(true)
                .write(true)
                .mode(0o600)
                .custom_flags(libc::O_NOFOLLOW)
                .open(&tmp)
                .map_err(|_| "private_write_failed")?;
            f.write_all(data)
                .and_then(|_| f.sync_all())
                .map_err(|_| "private_write_failed")?;
            fs::rename(&tmp, self.root.join(name)).map_err(|_| "private_commit_failed")?;
            File::open(&self.root)
                .and_then(|d| d.sync_all())
                .map_err(|_| "private_commit_failed")?;
            Ok(())
        })();
        if result.is_err() {
            let _ = fs::remove_file(&tmp);
        }
        result
    }
    pub fn catalog(&self) -> Result<Catalog, String> {
        let mut c: Catalog = match self.read("catalog.json")? {
            Some(b) => serde_json::from_slice(&b).map_err(|_| "invalid_catalog")?,
            None => Catalog {
                revision: 0,
                nodes: vec![],
                current: None,
            },
        };
        for n in &mut c.nodes {
            let id = n.id.clone();
            n.validate()?;
            if id != n.id {
                return Err("catalog_integrity_failed".into());
            }
        }
        if let Some(id) = self.applied()?.get("node_id").and_then(|v| v.as_str()) {
            c.current = Some(id.to_owned());
        }
        Ok(c)
    }
    pub fn applied(&self) -> Result<serde_json::Value, String> {
        let active = self.read("active.json")?;
        let metadata = self.read("applied.json")?;
        if let (Some(active), Some(metadata)) = (active, metadata) {
            let v: serde_json::Value =
                serde_json::from_slice(&metadata).map_err(|_| "invalid_applied_metadata")?;
            if v["sha256"] == format!("{:x}", Sha256::digest(active)) {
                return Ok(serde_json::json!({"node_id":v["node_id"],"mode":v["mode"]}));
            }
        }
        Ok(serde_json::Value::Null)
    }
    pub fn stage(&self, p: &ImportPreview) -> Result<String, String> {
        let c = self.catalog()?;
        if p.nodes.is_empty() {
            return Err("empty_catalog".into());
        }
        let staged = serde_json::to_vec(&serde_json::json!({"base":c.revision,"preview":p}))
            .map_err(|_| "invalid_catalog")?;
        let id = format!("{:x}", Sha256::digest(&staged));
        self.write("preview.json", &staged)?;
        Ok(id)
    }
    pub fn staged_public(&self) -> Result<serde_json::Value, String> {
        let data = self.read("preview.json")?.ok_or("no_preview")?;
        let staged: Staged = serde_json::from_slice(&data).map_err(|_| "invalid_preview")?;
        let c = self.catalog()?;
        let old = ImportPreview { nodes: c.nodes }.public();
        let diff = preview_replace(&staged.preview, &old, c.current.as_deref(), true)?;
        Ok(
            serde_json::json!({"preview_id":format!("{:x}",Sha256::digest(data)),"nodes":staged.preview.public(),"diff":diff,"base_revision":staged.base}),
        )
    }
    pub fn commit(&self, id: &str, confirmed: bool) -> Result<Catalog, String> {
        if !confirmed {
            return Err("confirmation_required".into());
        }
        let data = self.read("preview.json")?.ok_or("no_preview")?;
        if format!("{:x}", Sha256::digest(&data)) != id {
            return Err("preview_conflict".into());
        }
        let staged: Staged = serde_json::from_slice(&data).map_err(|_| "invalid_preview")?;
        let c = self.catalog()?;
        if c.revision != staged.base {
            return Err("catalog_revision_conflict".into());
        }
        let p = crate::catalog::import_preview(
            &serde_json::to_vec(&staged.preview.nodes).map_err(|_| "invalid_preview")?,
            crate::catalog::ImportFormat::LegacyJson,
        )?;
        let current = c.current.filter(|id| p.nodes.iter().any(|n| &n.id == id));
        let next = Catalog {
            revision: c.revision + 1,
            nodes: p.nodes,
            current,
        };
        self.write(
            "catalog.json",
            &serde_json::to_vec(&next).map_err(|_| "invalid_catalog")?,
        )?;
        Ok(next)
    }
}
fn filename(name: &str) -> bool {
    !name.is_empty()
        && name.len() < 100
        && name
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'.' || b == b'-')
        && name != "."
        && name != ".."
}
