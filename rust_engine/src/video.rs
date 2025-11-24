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
        // Initialize without crashing if already inited
        ffmpeg::init().ok();

        let ictx = input(&path).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        let stream = ictx.streams().best(Type::Video).ok_or_else(|| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("No video stream found")
        })?;

        // Initialize Decoder
        let context = ffmpeg::codec::context::Context::from_parameters(stream.parameters())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        let decoder = context.decoder().video()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        // --- SAFE MATH (Avoids Cast Errors) ---
        // 1. TimeBase: Use standard FROM implementation
        let time_base = f64::from(stream.time_base()); 
        
        // 2. Duration: Stream duration is ticks, convert to seconds
        let ticks = stream.duration();
        let duration = if ticks > 0 { ticks as f64 * time_base } else { 0.0 };
        
        // 3. FPS
        let fps = f64::from(stream.avg_frame_rate());

        Ok(VideoClip {
            path,
            width: decoder.width(),
            height: decoder.height(),
            duration,
            fps: if fps > 0.0 { fps } else { 30.0 }, // Fallback
        })
    }

    /// FEATURE: PROXIES
    /// Returns a list of low-res bytes for drawing timelines
    fn get_timeline_strip<'py>(&self, py: Python<'py>, count: usize, width: u32, height: u32) -> PyResult<Vec<Py<PyBytes>>> {
        let mut ictx = input(&self.path).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        let stream = ictx.streams().best(Type::Video).unwrap();
        let stream_idx = stream.index();
        let duration_raw = stream.duration();

        let mut decoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters())
            .unwrap().decoder().video().unwrap();

        // Bilinear is faster for small thumbnails
        let mut scaler = Context::get(
            decoder.format(), decoder.width(), decoder.height(),
            Pixel::RGB24, width, height, Flags::BILINEAR
        ).unwrap();

        let mut results = Vec::with_capacity(count);
        
        // Safety Math for stepping
        let step = if count > 0 && duration_raw > 0 { duration_raw / count as i64 } else { 0 };

        for i in 0..count {
            let target_ts = (i as i64 * step).max(0);
            
            // "fire and forget" seek
            let _ = ictx.seek(target_ts, ..target_ts);

            let mut decoded = Video::empty();
            let mut rgb = Video::empty();
            let mut found = false;

            // Packet loop
            for (s, packet) in ictx.packets() {
                if s.index() == stream_idx {
                    decoder.send_packet(&packet).ok();
                    if decoder.receive_frame(&mut decoded).is_ok() {
                        if scaler.run(&decoded, &mut rgb).is_ok() {
                            // Manual Buffer Copy to ensure RGB structure
                            let data = rgb.data(0);
                            let stride = rgb.stride(0);
                            let mut buf = Vec::with_capacity((width * height * 3) as usize);
                            
                            for y in 0..height {
                                let start = y as usize * stride;
                                let end = start + (width as usize * 3);
                                if end <= data.len() {
                                    buf.extend_from_slice(&data[start..end]);
                                }
                            }
                            results.push(PyBytes::new_bound(py, &buf).into());
                            found = true;
                            break; 
                        }
                    }
                }
            }
            // Padding if missing (duplicate previous)
            if !found {
                 if let Some(last) = results.last() { results.push(last.clone()); }
                 else { results.push(PyBytes::new_bound(py, &vec![0u8; (width*height*3) as usize]).into()); }
            }
        }
        Ok(results)
    }

    /// FEATURE: FAST SCRUB
    /// Jumps to nearest keyframe. Not precise, but Instant (0s delay).
    /// Used for sliding the seek bar.
    fn get_keyframe<'py>(&self, py: Python<'py>, time_secs: f64, width: u32, height: u32) -> PyResult<Py<PyBytes>> {
        let mut ictx = input(&self.path).unwrap();
        let stream = ictx.streams().best(Type::Video).unwrap();
        
        let time_base = f64::from(stream.time_base());
        let ts = if time_base > 0.0 { (time_secs / time_base) as i64 } else { 0 };
        
        // Fast seek to nearest keyframe
        let _ = ictx.seek(ts, ..ts); 

        let mut decoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters())
            .unwrap().decoder().video().unwrap();
        let mut scaler = Context::get(
            decoder.format(), decoder.width(), decoder.height(),
            Pixel::RGB24, width, height, Flags::FAST_BILINEAR // Use Fast Bilinear for UI
        ).unwrap();

        for (s, packet) in ictx.packets() {
            if s.index() == stream.index() {
                decoder.send_packet(&packet).ok();
                let mut decoded = Video::empty();
                if decoder.receive_frame(&mut decoded).is_ok() {
                    let mut rgb = Video::empty();
                    scaler.run(&decoded, &mut rgb).ok();
                    
                    let data = rgb.data(0);
                    let stride = rgb.stride(0);
                    let mut buf = Vec::new();
                    for y in 0..height {
                        let i = y as usize * stride;
                        let e = i + (width as usize * 3);
                        if e <= data.len() { buf.extend_from_slice(&data[i..e]); }
                    }
                    return Ok(PyBytes::new_bound(py, &buf).into());
                }
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Frame decode error"))
    }

    /// FEATURE: PRECISE RENDERING FRAME
    /// Scans accurately to specific timestamp. Slower, but used for Final Export.
    fn get_exact_frame<'py>(&self, py: Python<'py>, time_secs: f64, width: u32, height: u32) -> PyResult<Py<PyBytes>> {
        let mut ictx = input(&self.path).unwrap();
        let stream = ictx.streams().best(Type::Video).unwrap();
        let idx = stream.index();
        let time_base = f64::from(stream.time_base());
        let target_pts = if time_base > 0.0 { (time_secs / time_base) as i64 } else { 0 };
        
        let _ = ictx.seek(target_pts, ..target_pts); 
        
        let mut decoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters()).unwrap().decoder().video().unwrap();
        let mut scaler = Context::get(decoder.format(), decoder.width(), decoder.height(), Pixel::RGB24, width, height, Flags::BICUBIC).unwrap(); // High Quality Bicubic

        for (s, packet) in ictx.packets() {
            if s.index() == idx {
                decoder.send_packet(&packet).ok();
                let mut decoded = Video::empty();
                while decoder.receive_frame(&mut decoded).is_ok() {
                    // Check if we reached the frame
                    let pts = decoded.pts().unwrap_or(0);
                    if pts >= target_pts {
                        let mut rgb = Video::empty();
                        scaler.run(&decoded, &mut rgb).ok();
                        let data = rgb.data(0);
                        let stride = rgb.stride(0);
                        let mut buf = Vec::with_capacity((width*height*3) as usize);
                        for y in 0..height {
                            let i = y as usize * stride;
                            let e = i + (width as usize * 3);
                            if e <= data.len() { buf.extend_from_slice(&data[i..e]); }
                        }
                        return Ok(PyBytes::new_bound(py, &buf).into());
                    }
                }
            }
        }
        Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("EOF/No Frame"))
    }
}