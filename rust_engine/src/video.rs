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
        ffmpeg::init().ok(); // Ignore errors here, just proceed
        let ictx = input(&path).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        let stream = ictx.streams().best(Type::Video).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("No video stream")
        })?;

        let context = ffmpeg::codec::context::Context::from_parameters(stream.parameters()).unwrap();
        let decoder = context.decoder().video().unwrap();
        let w = decoder.width();
        let h = decoder.height();

        // --- THE "REMOVE IT" FIX ---
        // Instead of doing manual math (which caused your crash),
        // we use the generic "From" implementation directly.
        
        // 1. Timebase (Converts "1/30" to 0.033)
        let time_base = f64::from(stream.time_base()); 
        
        // 2. Duration (Integers * Timebase)
        let dur_ticks = stream.duration();
        let duration = if dur_ticks > 0 { dur_ticks as f64 * time_base } else { 0.0 };
        
        // 3. FPS
        let fps = f64::from(stream.avg_frame_rate());

        Ok(VideoClip {
            path,
            width: w,
            height: h,
            duration, // If invalid, it defaults to 0.0 safely
            fps: if fps > 0.0 { fps } else { 30.0 },
        })
    }

    /// Generates thumbnail list
    fn get_timeline_strip<'py>(&self, py: Python<'py>, count: usize, width: u32, height: u32) -> PyResult<Vec<Py<PyBytes>>> {
        let mut ictx = input(&self.path).unwrap();
        let stream = ictx.streams().best(Type::Video).unwrap();
        let dur = stream.duration();
        let stream_idx = stream.index();
        
        let mut decoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters()).unwrap().decoder().video().unwrap();
        let mut scaler = Context::get(decoder.format(), decoder.width(), decoder.height(), Pixel::RGB24, width, height, Flags::BILINEAR).unwrap();

        let mut res = Vec::new();
        // Safe step calculation (no casting nonsense)
        let step = if count > 0 && dur > 0 { dur / count as i64 } else { 0 };

        for i in 0..count {
            let t = (i as i64 * step).max(0);
            let _ = ictx.seek(t, ..t); // Force ignore result

            let mut decoded = Video::empty();
            let mut rgb = Video::empty();
            let mut found = false;
            
            for (s, p) in ictx.packets() {
                if s.index() == stream_idx {
                    decoder.send_packet(&p).ok();
                    if decoder.receive_frame(&mut decoded).is_ok() {
                        scaler.run(&decoded, &mut rgb).ok();
                        let d = rgb.data(0);
                        let stride = rgb.stride(0);
                        let mut buf = Vec::with_capacity((width*height*3) as usize);
                        
                        for y in 0..height {
                            let idx = y as usize * stride;
                            let end = idx + (width as usize * 3);
                            if end <= d.len() { buf.extend_from_slice(&d[idx..end]); }
                        }
                        res.push(PyBytes::new_bound(py, &buf).into());
                        found = true;
                        break;
                    }
                }
            }
            if !found {
                if let Some(prev) = res.last() { res.push(prev.clone()); }
                else { res.push(PyBytes::new_bound(py, &vec![0; (width*height*3) as usize]).into()); }
            }
        }
        Ok(res)
    }

    /// Fast Scrub
    fn get_keyframe<'py>(&self, py: Python<'py>, sec: f64, w: u32, h: u32) -> PyResult<Py<PyBytes>> {
        let mut ictx = input(&self.path).unwrap();
        let stream = ictx.streams().best(Type::Video).unwrap();
        let tb = f64::from(stream.time_base());
        let ts = if tb > 0.0 { (sec / tb) as i64 } else { 0 };

        let _ = ictx.seek(ts, ..ts); // Ignore output
        let mut decoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters()).unwrap().decoder().video().unwrap();
        let mut scaler = Context::get(decoder.format(), decoder.width(), decoder.height(), Pixel::RGB24, w, h, Flags::FAST_BILINEAR).unwrap();

        for (s, p) in ictx.packets() {
            if s.index() == stream.index() {
                decoder.send_packet(&p).ok();
                let mut d = Video::empty();
                if decoder.receive_frame(&mut d).is_ok() {
                    let mut r = Video::empty();
                    scaler.run(&d, &mut r).ok();
                    let dt = r.data(0);
                    let st = r.stride(0);
                    let mut b = Vec::new();
                    for y in 0..h {
                        let i = y as usize * st;
                        let e = i + (w as usize * 3);
                        if e <= dt.len() { b.extend_from_slice(&dt[i..e]); }
                    }
                    return Ok(PyBytes::new_bound(py, &b).into());
                }
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("No frame"))
    }
}