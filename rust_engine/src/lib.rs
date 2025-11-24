use pyo3::prelude::*;

mod clip;
mod internal;

use clip::AudioClip;

// The signature must accept a `&Bound<'_, PyModule>`
#[pymodule]
fn kanha_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<AudioClip>()?;
    Ok(())
}

// I am fed up with this Rust-Python interop stuff.
// Just make it work somehow.
// - Lakshmi Narayan
// Oh, and yes, please, if you really like this project by a teen, consider starring it on GitHub!
// and subscribing to my YouTube channel "Kanha Talks" where, i am planning to post most of my coding projects.
// Thank you!
// Made with ❤️ by a Barian
// For BARI English Academy
// https://thebari.in/