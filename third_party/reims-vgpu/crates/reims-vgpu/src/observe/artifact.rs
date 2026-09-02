//! Opt-in, bounded evidence for contracts rejected before the GPU can run.
//!
//! Raw guest descriptors and translated shaders are private diagnostic data,
//! not repository fixtures. Keep them in a process-owned temporary directory,
//! with owner-only permissions, and never overwrite a previous capture. This
//! gate does not change descriptor decoding, shader translation or execution.

use std::collections::HashSet;
use std::hash::{Hash, Hasher};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};

// Diagnostic budgets, not protocol limits. Exhaustion stops capture, not work.
const MAX_CAPTURE_BYTES: usize = 4 * 1024 * 1024;
const MAX_TOTAL_BYTES: usize = 32 * 1024 * 1024;
const MAX_CAPTURES: usize = 128;

#[derive(Clone, Copy, Debug, Hash)]
pub(crate) enum Kind {
    TextureDescriptor,
    VertexShader,
    FragmentShader,
}

impl Kind {
    fn suffix(self) -> &'static str {
        match self {
            Self::TextureDescriptor => "texture.bin",
            Self::VertexShader => "vertex.spv",
            Self::FragmentShader => "fragment.spv",
        }
    }
}

pub(crate) fn enabled() -> bool {
    matches!(
        std::env::var("REIMS_VGPU_CAPTURE_REJECTED_CONTRACTS").as_deref(),
        Ok("YES")
    )
}

#[derive(Default)]
struct Budget {
    seen: HashSet<u64>,
    bytes: usize,
}

impl Budget {
    fn admit(&mut self, key: u64, len: usize) -> bool {
        if len == 0
            || len > MAX_CAPTURE_BYTES
            || self.seen.len() >= MAX_CAPTURES
            || len > MAX_TOTAL_BYTES.saturating_sub(self.bytes)
            || self.seen.contains(&key)
        {
            return false;
        }
        self.bytes += len;
        self.seen.insert(key);
        true
    }
}

fn private_directory(path: &Path) -> std::io::Result<()> {
    let mut builder = std::fs::DirBuilder::new();
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt;
        builder.mode(0o700);
    }
    // AlreadyExists is a refusal too: never adopt an old/symlinked directory.
    builder.create(path)
}

fn private_file(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let mut options = std::fs::OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    options.open(path)?.write_all(bytes)
}

struct Store {
    directory: PathBuf,
    budget: Budget,
}

impl Store {
    fn new(directory: PathBuf) -> std::io::Result<Self> {
        private_directory(&directory)?;
        Ok(Self {
            directory,
            budget: Budget::default(),
        })
    }

    fn save(
        &mut self,
        kind: Kind,
        metadata: &str,
        bytes: &[u8],
    ) -> std::io::Result<Option<PathBuf>> {
        let mut hash = std::collections::hash_map::DefaultHasher::new();
        kind.hash(&mut hash);
        // Keep the first context for each byte-identical artifact. Dimensions
        // or resource ids changing across draws must not crowd out a new shader.
        bytes.hash(&mut hash);
        let Some(total) = bytes.len().checked_add(metadata.len()) else {
            return Ok(None);
        };
        if !self.budget.admit(hash.finish(), total) {
            return Ok(None);
        }
        let path = self
            .directory
            .join(format!("{:04}-{}", self.budget.seen.len(), kind.suffix()));
        // A failed write still consumes its budget, so an unwritable disk does
        // not turn the diagnostic into an unlimited stream of attempts.
        private_file(&path, bytes)?;
        private_file(&path.with_extension("txt"), metadata.as_bytes())?;
        Ok(Some(path))
    }
}

pub(crate) fn capture(kind: Kind, metadata: &str, bytes: &[u8]) {
    if !enabled() {
        return;
    }
    static STORE: OnceLock<Mutex<Option<Store>>> = OnceLock::new();
    let store = STORE.get_or_init(|| {
        let directory =
            std::env::temp_dir().join(format!("reims-vgpu-contract-{}", std::process::id()));
        Mutex::new(match Store::new(directory) {
            Ok(store) => Some(store),
            Err(error) => {
                super::fail(format!(
                    "contract_capture_failed reason=create_private_directory error={error:?}"
                ));
                None
            }
        })
    });
    let mut guard = store.lock().unwrap_or_else(|e| e.into_inner());
    let Some(store) = guard.as_mut() else {
        return;
    };
    match store.save(kind, metadata, bytes) {
        Ok(Some(path)) => super::fail(format!(
            "contract_capture kind={kind:?} bytes={} path={}",
            bytes.len(),
            path.display()
        )),
        Ok(None) => {}
        Err(error) => {
            if super::first_sight("contract_capture_write_failed", 0) {
                super::fail(format!(
                    "contract_capture_failed reason=write_private_artifact error={error:?}"
                ));
            }
        }
    }
}

pub(crate) fn capture_shader(kind: Kind, metadata: &str, words: &[u32]) {
    if !enabled() || words.len() > MAX_CAPTURE_BYTES / 4 {
        return;
    }
    let bytes: Vec<u8> = words.iter().flat_map(|w| w.to_le_bytes()).collect();
    capture(kind, metadata, &bytes);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn budget_rejects_empty_oversize_and_duplicate_without_spending() {
        let mut budget = Budget::default();
        assert!(!budget.admit(1, 0));
        assert!(!budget.admit(1, MAX_CAPTURE_BYTES + 1));
        assert!(budget.admit(1, 7));
        assert!(!budget.admit(1, 8));
        assert_eq!(budget.bytes, 7);
        assert_eq!(budget.seen.len(), 1);
    }

    #[test]
    fn budget_caps_total_bytes_and_capture_count_independently() {
        let mut bytes = Budget::default();
        for n in 0..MAX_TOTAL_BYTES / MAX_CAPTURE_BYTES {
            assert!(bytes.admit(n as u64, MAX_CAPTURE_BYTES));
        }
        assert!(!bytes.admit(u64::MAX, 1));
        let mut count = Budget::default();
        for n in 0..MAX_CAPTURES {
            assert!(count.admit(n as u64, 1));
        }
        assert!(!count.admit(u64::MAX, 1));
    }

    #[test]
    fn private_artifacts_are_exact_deduplicated_and_never_overwritten() {
        let parent =
            std::env::temp_dir().join(format!("reims-contract-test-{}", std::process::id()));
        let mut store = Store::new(parent.clone()).expect("fresh diagnostic test directory");
        assert!(Store::new(parent.clone()).is_err());
        let path = store
            .save(Kind::TextureDescriptor, "length=3\n", &[0, 128, 255])
            .unwrap()
            .unwrap();
        assert_eq!(std::fs::read(&path).unwrap(), [0, 128, 255]);
        assert_eq!(
            std::fs::read_to_string(path.with_extension("txt")).unwrap(),
            "length=3\n"
        );
        assert!(store
            .save(Kind::TextureDescriptor, "length=3\n", &[0, 128, 255])
            .unwrap()
            .is_none());
        assert!(store
            .save(Kind::TextureDescriptor, "different draw\n", &[0, 128, 255])
            .unwrap()
            .is_none());
        assert!(private_file(&path, b"overwrite").is_err());
        assert_eq!(std::fs::read(&path).unwrap(), [0, 128, 255]);
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                std::fs::metadata(&parent).unwrap().permissions().mode() & 0o777,
                0o700
            );
            assert_eq!(
                std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
                0o600
            );
        }
        std::fs::remove_dir_all(parent).unwrap();
    }
}
