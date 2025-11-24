use pyo3::prelude::*;
use pyo3::types::PyBytes;
use ffmpeg_next as ffmpeg;
use ffmpeg::format::{input, Pixel};
use ffmpeg::media::Type;
use ffmpeg::software::scaling::{context::Context, flag::Flags};
use ffmpeg::util::frame::video::Video;

#[pyclass]
pub struct VideoClip {
    path: String,
    #[pyo3(get)]
    width: u32,
    #[pyo3(get)]
    height: u32,
    #[pyo3(get)]
    duration: f64,
    #[pyo3(get)]
    fps: f64,
}

#[pymethods]
impl VideoClip {
    #[new]
    fn new(path: String) -> PyResult<Self> {
        ffmpeg::init().map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let ictx = input(&path).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        let stream = ictx.streams().best(Type::Video).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("No video stream found")
        })?;

        // Context Decoder Setup
        let context = ffmpeg::codec::context::Context::from_parameters(stream.parameters())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let decoder = context.decoder().video()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        // --- FIXED: Manual Time Calculation (No Cast Errors) ---
        
        // 1. Time Base
        let tb = stream.time_base();
        let time_base = if tb.denominator() > 0 {
             tb.numerator() as f64 / tb.denominator() as f64
        } else {
             0.0
        };

        // 2. Duration (Integers to Float)
        let raw_duration = stream.duration();
        // Multiply int64 ticks by float timebase
        let duration = if raw_duration > 0 {
            (raw_duration as f64) * time_base
        } else {
            0.0
        };

        // 3. FPS
        let rate = stream.avg_frame_rate();
        let fps = if rate.denominator() > 0 {
            rate.numerator() as f64 / rate.denominator() as f64
        } else {
            30.0
        };

        Ok(VideoClip {
            path,
            width: decoder.width(),
            height: decoder.height(),
            duration: if duration < 0.0 { 0.0 } else { duration }, // Sanity clamp
            fps,
        })
    }

    /// TIMELINE THUMBNAILS (Low Res, List of Frames)
    fn get_timeline_strip<'py>(&self, py: Python<'py>, count: usize, width: u32, height: u32) -> PyResult<Vec<Py<PyBytes>>> {
        let mut ictx = input(&self.path).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        let stream_idx = ictx.streams().best(Type::Video).unwrap().index();
        let dur = ictx.streams().best(Type::Video).unwrap().duration();
        
        let stream = ictx.streams().best(Type::Video).unwrap();
        let mut decoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters())
            .unwrap().decoder().video().unwrap();

        let mut scaler = Context::get(
            decoder.format(), decoder.width(), decoder.height(),
            Pixel::RGB24, width, height, Flags::BILINEAR
        ).unwrap();

        let mut results = Vec::with_capacity(count);
        
        // Manual Math for step size to safely ignore mismatched types
        let step = if dur > 0 { dur / count as i64 } else { 0 };

        for i in 0..count {
            let target = (i as i64 * step).max(0);
            let _ = ictx.seek(target, ..target); // Use _ to explicitly ignore result
            
            let mut decoded = Video::empty();
            let mut rgb = Video::empty();
            let mut found = false;

            for (s, packet) in ictx.packets() {
                if s.index() == stream_idx {
                    let _ = decoder.send_packet(&packet);
                    if decoder.receive_frame(&mut decoded).is_ok() {
                        if scaler.run(&decoded, &mut rgb).is_ok() {
                             let data = rgb.data(0);
                             let stride = rgb.stride(0);
                             let mut buf = Vec::with_capacity((width*height*3) as usize);
                             
                             // Row by Row Copy
                             for y in 0..height {
                                 let start = y as usize * stride;
                                 let end = start + (width as usize * 3);
                                 if end <= data.len() { buf.extend_from_slice(&data[start..end]); }
                             }
                             
                             results.push(PyBytes::new_bound(py, &buf).into());
                             found = true;
                             break;
                        }
                    }
                }
            }
            if !found {
                 if let Some(prev) = results.last() { results.push(prev.clone()); }
                 else { results.push(PyBytes::new_bound(py, &vec![0u8; (width*height*3) as usize]).into()); }
            }
        }
        Ok(results)
    }

    /// FAST SCRUB (Keyframe only)
    fn get_keyframe<'py>(&self, py: Python<'py>, time_secs: f64, w: u32, h: u32) -> PyResult<Py<PyBytes>> {
        let mut ictx = input(&self.path).unwrap();
        let stream = ictx.streams().best(Type::Video).unwrap();
        
        let tb_rat = stream.time_base();
        let tb = if tb_rat.denominator() > 0 {
             tb_rat.numerator() as f64 / tb_rat.denominator() as f64
        } else { 0.0 };

        let ts = if tb > 0.0 { (time_secs / tb) as i64 } else { 0 };
        let _ = ictx.seek(ts, ..ts);
        
        let mut decoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters()).unwrap().decoder().video().unwrap();
        let mut scaler = Context::get(decoder.format(), decoder.width(), decoder.height(), Pixel::RGB24, w, h, Flags::FAST_BILINEAR).unwrap();
        
        for (s, pkt) in ictx.packets() {
            if s.index() == stream.index() {
                let _ = decoder.send_packet(&pkt);
                let mut d = Video::empty();
                if decoder.receive_frame(&mut d).is_ok() {
                    let mut r = Video::empty();
                    scaler.run(&d, &mut r).ok();
                    
                    let data = r.data(0);
                    let stride = r.stride(0);
                    let mut b = Vec::new();
                    for y in 0..h {
                        let i = y as usize * stride;
                        let j = i + (w as usize * 3);
                        if j <= data.len() { b.extend_from_slice(&data[i..j]); }
                    }
                    return Ok(PyBytes::new_bound(py, &b).into());
                }
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Frame error"))
    }
}