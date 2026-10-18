use omt_proxy::catalog::*;
use omt_proxy::storage::*;
use std::{
    fs,
    os::unix::fs::{PermissionsExt, symlink},
};
fn root() -> std::path::PathBuf {
    std::env::temp_dir().join(format!(
        "omt-store-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ))
}
fn nodes() -> ImportPreview {
    import_preview(b"vless://11111111-2222-3333-4444-555555555555@proxy.example:443?security=tls&type=ws#Example",ImportFormat::Uri).unwrap()
}
#[test]
fn preview_commit_is_private_and_does_not_set_running() {
    let p = root();
    let s = Store::open(&p).unwrap();
    let id = s.stage(&nodes()).unwrap();
    assert_eq!(s.catalog().unwrap().revision, 0);
    assert!(s.commit("wrong", true).is_err());
    let c = s.commit(&id, true).unwrap();
    assert_eq!(c.nodes.len(), 1);
    assert_eq!(c.current, None);
    assert_eq!(
        fs::metadata(p.join("catalog.json"))
            .unwrap()
            .permissions()
            .mode()
            & 0o777,
        0o600
    );
    assert_eq!(
        fs::metadata(&p).unwrap().permissions().mode() & 0o777,
        0o700
    );
    fs::remove_dir_all(p).unwrap();
}
#[test]
fn symlink_directory_and_secret_file_rejected() {
    let p = root();
    fs::create_dir(&p).unwrap();
    fs::set_permissions(&p, fs::Permissions::from_mode(0o700)).unwrap();
    let other = p.with_extension("link");
    symlink(&p, &other).unwrap();
    assert!(Store::open(&other).is_err());
    fs::write(p.join("target"), "{}").unwrap();
    symlink(p.join("target"), p.join("catalog.json")).unwrap();
    let s = Store::open(&p).unwrap();
    assert!(s.catalog().is_err());
    fs::remove_file(other).unwrap();
    fs::remove_dir_all(p).unwrap();
}
#[test]
fn releasing_store_unlocks_even_during_concurrent_child_exec() {
    use std::os::fd::RawFd;
    let p = root();
    let store = Store::open(&p).unwrap();
    let mut pipe: [RawFd; 2] = [-1, -1];
    assert_eq!(
        unsafe { libc::pipe2(pipe.as_mut_ptr(), libc::O_CLOEXEC) },
        0
    );
    let child = unsafe { libc::fork() };
    assert!(child >= 0);
    if child == 0 {
        // Only async-signal-safe operations between fork and _exit.
        unsafe {
            libc::close(pipe[1]);
            let mut byte = 0u8;
            libc::read(pipe[0], &mut byte as *mut _ as *mut libc::c_void, 1);
            libc::_exit(0);
        }
    }
    unsafe {
        libc::close(pipe[0]);
    }
    drop(store);
    let reopened = Store::open(&p);
    unsafe {
        libc::write(pipe[1], b"x".as_ptr() as *const libc::c_void, 1);
        libc::close(pipe[1]);
        libc::waitpid(child, std::ptr::null_mut(), 0);
    }
    assert!(
        reopened.is_ok(),
        "store lock must be released before a forked child execs"
    );
    drop(reopened);
    fs::remove_dir_all(p).unwrap();
}
