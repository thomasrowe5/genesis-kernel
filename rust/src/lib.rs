use pyo3::prelude::*;

#[pyfunction]
fn add(a: i64, b: i64) -> PyResult<i64> {
    Ok(a + b)
}

#[pymodule]
fn genesis_kernel(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_works() {
        assert_eq!(add(2, 3).unwrap(), 5);
    }
}
