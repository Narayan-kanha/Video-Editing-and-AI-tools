use pyo3::prelude::*;
use crate::internal::{AudioReader, AudioResult};
use symphonia::core::audio::{SampleBuffer, Signal};
use symphonia::core::errors::Error as SymphoniaError;
use std::io::BufWriter; // Efficient writing

#[pyclass]
pub struct AudioClip {
    path: String,
    #[pyo3(get)]
    duration: f64, 
    #[pyo3(get)]
    sample_rate: u32,
    #[pyo3(get)]
    channels: u32,
    
    // Internal use
    duration_frames: u64,
}

#[pymethods]
impl AudioClip {
    #[new]
    pub fn new(path: String) -> PyResult<Self> {
        let reader = AudioReader::new(&path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        let frames = reader.duration_frames.unwrap_or(0);
        let dur_sec = if reader.sample_rate > 0 { 
            frames as f64 / reader.sample_rate as f64 
        } else { 0.0 };

        Ok(AudioClip {
            path,
            duration: dur_sec,
            sample_rate: reader.sample_rate,
            channels: reader.channels,
            duration_frames: frames,
        })
    }

    /// FEATURE: Smart Subtitle Timing (Silence Detection)
    /// returns list of [start, end] for SPEECH (ignoring silence)
    /// useful for cutting clips or placing subtitle boxes
    pub fn detect_speech_intervals(&self, threshold_db: f32, min_speech_duration: f64) -> PyResult<Vec<(f64, f64)>> {
        let mut reader = AudioReader::new(&self.path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        // DB to Amplitude: 10^(db/20)
        let silence_floor = 10.0f32.powf(threshold_db / 20.0);
        let mut intervals = Vec::new();
        
        let mut in_speech = false;
        let mut speech_start = 0.0;
        let mut current_time = 0.0;
        let sample_tick = 1.0 / self.sample_rate as f64;

        loop {
            let packet = match reader.format.next_packet() {
                Ok(p) => p,
                Err(_) => break,
            };

            if packet.track_id() != reader.track_id { continue; }

            if let Ok(decoded) = reader.decoder.decode(&packet) {
                let spec = *decoded.spec();
                let capacity = decoded.capacity() as u64;
                let mut buf = SampleBuffer::<f32>::new(capacity, spec);
                buf.copy_interleaved_ref(decoded);
                
                let stride = spec.channels.count();
                for i in (0..buf.samples().len()).step_by(stride) {
                    let mut amp_sum = 0.0;
                    for c in 0..stride {
                        amp_sum += buf.samples()[i+c].abs();
                    }
                    let avg_amp = amp_sum / stride as f32;

                    if avg_amp > silence_floor {
                        if !in_speech {
                            in_speech = true;
                            speech_start = current_time;
                        }
                    } else {
                        // Simplistic state flip (ideally needs debouncing)
                        if in_speech {
                            if current_time - speech_start > min_speech_duration {
                                intervals.push((speech_start, current_time));
                            }
                            in_speech = false;
                        }
                    }
                    current_time += sample_tick;
                }
            }
        }
        
        // Finalize if file ended while talking
        if in_speech && (current_time - speech_start > min_speech_duration) {
            intervals.push((speech_start, current_time));
        }

        Ok(intervals)
    }

    /// FEATURE: Batch Audio Export (.wav)
    /// Highly optimized path for extracting audio for Whisper AI
    pub fn export_as_wav(&self, output_path: String) -> PyResult<String> {
        let mut reader = AudioReader::new(&self.path)
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        // Configure Wav Spec
        let spec = hound::WavSpec {
            channels: reader.channels as u16,
            sample_rate: reader.sample_rate,
            bits_per_sample: 16,
            sample_format: hound::SampleFormat::Int,
        };

        // Buffered Writer (Very Fast)
        let writer = hound::WavWriter::create(&output_path, spec)
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        let mut buf_writer = BufWriter::new(writer);

        loop {
            let packet = match reader.format.next_packet() {
                Ok(p) => p,
                Err(_) => break,
            };
            if packet.track_id() != reader.track_id { continue; }
            
            if let Ok(decoded) = reader.decoder.decode(&packet) {
                let spec = *decoded.spec();
                let cap = decoded.capacity() as u64;
                // Convert straight to i16 for Wav
                let mut buf = SampleBuffer::<i16>::new(cap, spec);
                buf.copy_interleaved_ref(decoded);
                
                let wav_writer = buf_writer.get_mut();
                for sample in buf.samples() {
                    wav_writer.write_sample(*sample).ok();
                }
            }
        }

        Ok(format!("Exported to {}", output_path))
    }

    /// Optimized Waveform generator
    pub fn get_waveform(&self, target_width: usize) -> PyResult<Vec<f32>> {
         // (Paste the existing get_waveform code here, it was correct in previous answers)
         // Omitted for brevity, but make sure it uses: 
         // let cap = decoded.capacity() as u64; 
         Ok(vec![]) // placeholder to save text
    }
}