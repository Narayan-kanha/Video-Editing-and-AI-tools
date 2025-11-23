use pyo3::prelude::*;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::probe::Hint;
use symphonia::core::codecs::{DecoderOptions, CODEC_TYPE_NULL};
use symphonia::core::formats::FormatOptions;
use symphonia::core::meta::MetadataOptions;
use std::fs::File;
use std::path::Path;

#[pyfunction]
fn get_waveform(path: String, target_width: usize) -> PyResult<Vec<f32>> {
    // 1. Open the file
    let src = File::open(Path::new(&path))?;
    let mss = MediaSourceStream::new(Box::new(src), Default::default());

    // 2. Probe (Guess format)
    let hint = Hint::new();
    let format_opts = FormatOptions::default();
    let metadata_opts = MetadataOptions::default();
    let decoder_opts = DecoderOptions::default();

    let probed = symphonia::default::get_probe()
        .format(&hint, mss, &format_opts, &metadata_opts)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

    let mut format = probed.format;

    // 3. Find Audio Track
    let track = format.tracks()
        .iter()
        .find(|t| t.codec_params.codec != CODEC_TYPE_NULL)
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("No audio track found"))?;

    let track_id = track.id;
    let mut decoder = symphonia::default::get_codecs()
        .make(&track.codec_params, &decoder_opts)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    // 4. DECODING LOOP
    let mut samples: Vec<f32> = Vec::new();

    loop {
        let packet = match format.next_packet() {
            Ok(packet) => packet,
            Err(symphonia::core::errors::Error::IoError(e)) if e.kind() == std::io::ErrorKind::UnexpectedEof => break, 
            Err(_) => break,
        };

        if packet.track_id() != track_id {
            continue;
        }

        match decoder.decode(&packet) {
            Ok(decoded) => {
                // --- LOGIC REORDERED HERE ---
                
                // 1. Get the Specs *FIRST* (Before moving `decoded`)
                let spec = *decoded.spec();
                let capacity = decoded.capacity() as u64;
                let stride = spec.channels.count(); 

                // 2. Create buffer with the saved spec
                let mut buf = symphonia::core::audio::SampleBuffer::<f32>::new(capacity, spec);
                
                // 3. NOW we move `decoded` into the buffer
                buf.copy_interleaved_ref(decoded);
                
                // 4. Use the `stride` we saved earlier
                for i in (0..buf.samples().len()).step_by(stride) {
                    samples.push(buf.samples()[i]);
                }
            }
            Err(_) => break,
        }
    }

    // 5. Process Data (Downsample)
    if samples.is_empty() {
        return Ok(vec![0.0; target_width]);
    }

    let chunk_size = samples.len() / target_width;
    let mut waveform = Vec::with_capacity(target_width);

    for i in 0..target_width {
        let start = i * chunk_size;
        let end = ((i + 1) * chunk_size).min(samples.len());
        
        if start >= end {
            waveform.push(0.0);
            continue;
        }

        let mut sum_sq = 0.0;
        for j in start..end {
            let s = samples[j];
            sum_sq += s * s;
        }
        let rms = (sum_sq / (end - start) as f32).sqrt();
        waveform.push(rms);
    }

    // Normalize
    let max_val = waveform.iter().fold(0.0f32, |a, &b| a.max(b));
    if max_val > 0.0 {
        for x in &mut waveform {
            *x /= max_val;
        }
    }

    Ok(waveform)
}

#[pymodule]
fn kanha_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_waveform, m)?)?;
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