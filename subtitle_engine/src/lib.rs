use pyo3::prelude::*;
use ffmpeg_next as ffmpeg;
// THE ONLY FIX IS ON THIS LINE: It's `Sample`, not `Type`.
use ffmpeg_next::format::Sample::{I16, I32, F32}; 

// Helper function to convert FFmpeg errors into Python errors
fn to_py_err(e: ffmpeg::Error) -> PyErr {
    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string())
}

#[pyfunction]
fn hello_from_rust() -> PyResult<String> {
    Ok("Rust Bridge is Active and Robust.".to_string())
}

#[pyfunction]
fn generate_waveform(path: &str, samples_per_point: usize) -> PyResult<Vec<f32>> {
    ffmpeg::init().map_err(to_py_err)?;

    if let Ok(mut ictx) = ffmpeg::format::input(&path) {
        let stream = ictx
            .streams()
            .best(ffmpeg::media::Type::Audio)
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Could not find an audio stream"))?;
        
        let stream_index = stream.index();
    
        let context_decoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters()).map_err(to_py_err)?;
        let mut decoder = context_decoder.decoder().audio().map_err(to_py_err)?;
    
        let mut peaks: Vec<f32> = Vec::new();
        let mut sample_buffer: Vec<f32> = Vec::with_capacity(samples_per_point);
    
        let mut decoded = ffmpeg::frame::Audio::empty();

        for (stream, packet) in ictx.packets() {
            if stream.index() == stream_index {
                decoder.send_packet(&packet).map_err(to_py_err)?;
                while decoder.receive_frame(&mut decoded).is_ok() {
                    // This section now works because the import above is correct
                    match decoded.format() {
                        I16(..) => { // 16-bit Signed Integer
                            let plane: &[i16] = decoded.plane(0);
                            for &sample in plane {
                                sample_buffer.push(sample as f32 / i16::MAX as f32);
                            }
                        },
                        F32(..) => { // 32-bit Float
                            let plane: &[f32] = decoded.plane(0);
                             for &sample in plane {
                                sample_buffer.push(sample);
                            }
                        },
                        I32(..) => { // 32-bit Signed Integer
                             let plane: &[i32] = decoded.plane(0);
                            for &sample in plane {
                                sample_buffer.push(sample as f32 / i32::MAX as f32);
                            }
                        },
                        _ => return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>("Unsupported audio sample format")),
                    }

                    while sample_buffer.len() >= samples_per_point {
                        let temp_chunk: Vec<f32> = sample_buffer.drain(0..samples_per_point).collect();
                        let peak = temp_chunk.iter().fold(0.0_f32, |acc, &x| acc.max(x.abs()));
                        peaks.push(peak);
                    }
                }
            }
        }
        
        Ok(peaks)
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyIOError, _>("Could not open media file"))
    }
}

#[pymodule]
fn subtitle_engine(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello_from_rust, m)?)?;
    m.add_function(wrap_pyfunction!(generate_waveform, m)?)?;
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