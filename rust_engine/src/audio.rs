use pyo3::prelude::*;
use crate::internal::{AudioReader, AudioResult};
use symphonia::core::audio::{SampleBuffer, Signal}; // Signal trait is important
use symphonia::core::errors::Error as SymphoniaError;
use std::io::BufWriter;

#[pyclass]
pub struct AudioClip {
    path: String,
    #[pyo3(get)]
    duration: f64,
    #[pyo3(get)]
    sample_rate: u32,
    #[pyo3(get)]
    channels: u32,
    // Private
    duration_frames: u64,
}

#[pymethods]
impl AudioClip {
    #[new]
    pub fn new(path: String) -> PyResult<Self> {
        let reader = AudioReader::new(&path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        let frames = reader.duration_frames.unwrap_or(0);
        let duration = if reader.sample_rate > 0 { frames as f64 / reader.sample_rate as f64 } else { 0.0 };

        Ok(AudioClip {
            path,
            duration,
            sample_rate: reader.sample_rate,
            channels: reader.channels,
            duration_frames: frames,
        })
    }

    /// WAVEFORM GENERATOR
    /// O(1) Memory usage. 
    /// Generates visual points for UI drawing.
    pub fn get_waveform(&self, target_width: usize) -> PyResult<Vec<f32>> {
        if target_width == 0 { return Ok(vec![]); }

        let mut reader = AudioReader::new(&self.path).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        let total_frames = self.duration_frames;
        if total_frames == 0 { return Ok(vec![0.0; target_width]); }

        let frames_per_pixel = (total_frames as f64 / target_width as f64).max(1.0);
        let mut waveform = vec![0.0; target_width];
        
        let mut pixel_idx = 0;
        let mut sum_sq = 0.0;
        let mut bucket_count = 0;
        let mut abs_idx = 0;

        loop {
            let packet = match reader.format.next_packet() {
                Ok(p) => p,
                Err(SymphoniaError::IoError(e)) if e.kind() == std::io::ErrorKind::UnexpectedEof => break,
                Err(_) => break,
            };

            if packet.track_id() != reader.track_id { continue; }

            if let Ok(decoded) = reader.decoder.decode(&packet) {
                let spec = *decoded.spec();
                let cap = decoded.capacity() as u64; // Strict Cast
                let mut buf = SampleBuffer::<f32>::new(cap, spec);
                buf.copy_interleaved_ref(decoded);
                
                let samples = buf.samples();
                let stride = spec.channels.count(); 

                // Iterate frame by frame (stride)
                for i in (0..samples.len()).step_by(stride) {
                    let mut amp = 0.0;
                    for c in 0..stride { amp += samples[i+c].abs(); }
                    amp /= stride as f32; // Mono Mixdown

                    // Binning Logic
                    let target = (abs_idx as f64 / frames_per_pixel).floor() as usize;
                    
                    if target != pixel_idx {
                        if pixel_idx < target_width && bucket_count > 0 {
                            waveform[pixel_idx] = (sum_sq / bucket_count as f32).sqrt();
                        }
                        pixel_idx = target;
                        sum_sq = 0.0;
                        bucket_count = 0;
                    }
                    if pixel_idx < target_width {
                        sum_sq += amp * amp;
                        bucket_count += 1;
                    }
                    abs_idx += 1;
                }
            }
            if pixel_idx > target_width { break; }
        }
        
        // Clean last bin
        if pixel_idx < target_width && bucket_count > 0 {
             waveform[pixel_idx] = (sum_sq / bucket_count as f32).sqrt();
        }

        // Normalize
        let max_val = waveform.iter().fold(0.0f32, |a, &b| a.max(b));
        if max_val > 0.0 { for x in &mut waveform { *x /= max_val; } }

        Ok(waveform)
    }

    /// EXPORT AUDIO TO WAV
    /// Requires [dependencies] hound = "3.5"
    pub fn export_as_wav(&self, output: String) -> PyResult<String> {
        let mut reader = AudioReader::new(&self.path).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        let spec = hound::WavSpec {
            channels: reader.channels as u16,
            sample_rate: reader.sample_rate,
            bits_per_sample: 16,
            sample_format: hound::SampleFormat::Int,
        };
        let writer = hound::WavWriter::create(&output, spec).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        let mut buffered = BufWriter::new(writer);

        loop {
            let packet = match reader.format.next_packet() { Ok(p) => p, Err(_) => break };
            if packet.track_id() != reader.track_id { continue; }
            if let Ok(decoded) = reader.decoder.decode(&packet) {
                let spec = *decoded.spec();
                let cap = decoded.capacity() as u64;
                let mut buf = SampleBuffer::<i16>::new(cap, spec);
                buf.copy_interleaved_ref(decoded);
                
                let w = buffered.get_mut();
                for s in buf.samples() { w.write_sample(*s).ok(); }
            }
        }
        Ok(format!("Exported: {}", output))
    }

    /// SILENCE/SPEECH DETECTOR
    /// Returns [(start, end)] of active speech
    pub fn detect_speech_intervals(&self, db_thresh: f32, min_dur: f64) -> PyResult<Vec<(f64, f64)>> {
        let mut reader = AudioReader::new(&self.path).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        let floor = 10.0f32.powf(db_thresh / 20.0);
        let mut intervals = Vec::new();
        
        let mut active = false;
        let mut start_t = 0.0;
        let mut curr_t = 0.0;
        let step = 1.0 / self.sample_rate as f64;

        loop {
            let packet = match reader.format.next_packet() { Ok(p) => p, Err(_) => break };
            if packet.track_id() != reader.track_id { continue; }
            if let Ok(decoded) = reader.decoder.decode(&packet) {
                let spec = *decoded.spec();
                let cap = decoded.capacity() as u64;
                let mut buf = SampleBuffer::<f32>::new(cap, spec);
                buf.copy_interleaved_ref(decoded);
                let stride = spec.channels.count();
                
                for i in (0..buf.samples().len()).step_by(stride) {
                    let mut sum = 0.0;
                    for c in 0..stride { sum += buf.samples()[i+c].abs(); }
                    let val = sum / stride as f32;

                    if val > floor {
                        if !active { active = true; start_t = curr_t; }
                    } else {
                        // Deactivate
                        if active {
                             if curr_t - start_t > min_dur { intervals.push((start_t, curr_t)); }
                             active = false;
                        }
                    }
                    curr_t += step;
                }
            }
        }
        if active && (curr_t - start_t > min_dur) { intervals.push((start_t, curr_t)); }
        Ok(intervals)
    }
}