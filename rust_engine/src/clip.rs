use pyo3::prelude::*;
use crate::internal::{AudioReader, AudioResult};
use symphonia::core::audio::SampleBuffer;
use symphonia::core::errors::Error as SymphoniaError;

#[pyclass]
pub struct AudioClip {
    path: String,
    
    // Metadata (ReadOnly)
    #[pyo3(get)]
    duration_frames: u64,
    #[pyo3(get)]
    sample_rate: u32,
    #[pyo3(get)]
    channels: u32,
    #[pyo3(get)]
    duration: f64, 

    // --- EFFECTS --- 
    // We make these get/set so Python can change them
    #[pyo3(get, set)]
    volume: f32,       // 1.0 = 100%
    #[pyo3(get, set)]
    fade_in: f64,      // seconds
    #[pyo3(get, set)]
    fade_out: f64,     // seconds
}

#[pymethods]
impl AudioClip {
    #[new]
    #[pyo3(signature = (path))] // defaults can be added here
    pub fn new(path: String) -> PyResult<Self> {
        let reader = AudioReader::new(&path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        let frames = reader.duration_frames.unwrap_or(0);
        let dur_sec = if reader.sample_rate > 0 { 
            frames as f64 / reader.sample_rate as f64 
        } else { 
            0.0 
        };

        Ok(AudioClip {
            path,
            duration_frames: frames,
            sample_rate: reader.sample_rate,
            channels: reader.channels,
            duration: dur_sec,
            
            // Default Effects values
            volume: 1.0,
            fade_in: 0.0,
            fade_out: 0.0,
        })
    }

    /// Generates waveform WITH effects applied
    pub fn get_waveform(&self, target_width: usize) -> PyResult<Vec<f32>> {
        if target_width == 0 { return Ok(vec![]); }

        // Open Stream
        let mut reader = AudioReader::new(&self.path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Error: {}", e)))?;

        let total_frames = self.duration_frames;
        if total_frames == 0 { return Ok(vec![0.0; target_width]); }

        let frames_per_pixel = (total_frames as f64 / target_width as f64).max(1.0);
        let mut waveform = vec![0.0; target_width];
        let mut pixel_index = 0;
        
        let mut current_sum_sq: f32 = 0.0;
        let mut count_in_bucket: u32 = 0;
        let mut absolute_frame_idx: u64 = 0;

        // Pre-calc effect frames
        let fade_in_frames = (self.fade_in * self.sample_rate as f64) as u64;
        let fade_out_start_frame = if self.fade_out > 0.0 {
            total_frames.saturating_sub((self.fade_out * self.sample_rate as f64) as u64)
        } else {
            total_frames
        };

        loop {
            // Get Packet
            let packet = match reader.format.next_packet() {
                Ok(pkt) => pkt,
                Err(SymphoniaError::IoError(e)) if e.kind() == std::io::ErrorKind::UnexpectedEof => break,
                Err(_) => break,
            };

            if packet.track_id() != reader.track_id { continue; }

            // Decode
            match reader.decoder.decode(&packet) {
                Ok(decoded) => {
                    let spec = *decoded.spec();
                    let mut buf = SampleBuffer::<f32>::new(decoded.capacity() as u64, spec);
                    buf.copy_interleaved_ref(decoded);
                    let samples = buf.samples();
                    let channels = spec.channels.count();

                    // Step through Audio Frames
                    for i in (0..samples.len()).step_by(channels) {
                        
                        // 1. RAW Mix Down
                        let mut frame_amp = 0.0;
                        for c in 0..channels {
                             frame_amp += samples[i+c];
                        }
                        frame_amp /= channels as f32; // Average

                        // --- APPLY EFFECTS HERE ---

                        // Effect A: Fade In
                        if absolute_frame_idx < fade_in_frames {
                             let progress = absolute_frame_idx as f32 / fade_in_frames as f32;
                             frame_amp *= progress; // Multiply 0.0 to 1.0
                        }

                        // Effect B: Fade Out
                        if absolute_frame_idx >= fade_out_start_frame {
                            let dist_from_end = total_frames.saturating_sub(absolute_frame_idx);
                            let fade_len = total_frames - fade_out_start_frame;
                            let progress = dist_from_end as f32 / fade_len as f32;
                            frame_amp *= progress;
                        }

                        // Effect C: Volume/Gain
                        frame_amp *= self.volume;

                        // --------------------------

                        // Visual processing
                        let target_pixel = (absolute_frame_idx as f64 / frames_per_pixel).floor() as usize;

                        // Bin Change
                        if target_pixel != pixel_index {
                            if pixel_index < target_width && count_in_bucket > 0 {
                                let rms = (current_sum_sq / count_in_bucket as f32).sqrt();
                                waveform[pixel_index] = rms;
                            }
                            pixel_index = target_pixel;
                            current_sum_sq = 0.0;
                            count_in_bucket = 0;
                        }
                        
                        // Accumulate
                        if pixel_index < target_width {
                            current_sum_sq += frame_amp * frame_amp;
                            count_in_bucket += 1;
                        }
                        absolute_frame_idx += 1;
                    }
                },
                Err(_) => break,
            }
            if pixel_index > target_width { break; }
        }

        // Catch the last bin
        if pixel_index < target_width && count_in_bucket > 0 {
             waveform[pixel_index] = (current_sum_sq / count_in_bucket as f32).sqrt();
        }

        // Final Normalization
        let max_peak = waveform.iter().fold(0.0f32, |a, &b| a.max(b));
        if max_peak > 0.0001 {
            for x in &mut waveform {
                *x /= max_peak;
            }
        }

        Ok(waveform)
    }
}