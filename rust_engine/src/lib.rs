use pyo3::prelude::*;
mod internal;
mod audio;
mod video;
mod export;
mod effects; // <--- Register Effects

#[pymodule]
fn kanha_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<audio::AudioClip>()?;
    m.add_class::<video::VideoClip>()?;
    m.add_class::<export::VideoExporter>()?;
    m.add_class::<effects::ImageProcessor>()?; // <--- Add Class
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