//! Minimal PyO3 stub for cluster heartbeat orchestration.
use pyo3::prelude::*;

/// Represents a heartbeat status emitted by the Rust core.
#[pyclass]
pub struct Heartbeat {
    #[pyo3(get)]
    pub node_id: String,
    #[pyo3(get)]
    pub status: String,
}

#[pymethods]
impl Heartbeat {
    #[new]
    fn new(node_id: String, status: Option<String>) -> Self {
        Self {
            node_id,
            status: status.unwrap_or_else(|| "ready".to_string()),
        }
    }
}

/// Exported heartbeat utility returning a dummy status list.
#[pyfunction]
pub fn heartbeat_snapshot() -> PyResult<Vec<Heartbeat>> {
    Ok(vec![Heartbeat::new("node-0".into(), Some("ready".into()))])
}

/// Module definition required by PyO3.
#[pymodule]
fn libcluster(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_class::<Heartbeat>()?;
    m.add_function(wrap_pyfunction!(heartbeat_snapshot, m)?)?;
    Ok(())
}
