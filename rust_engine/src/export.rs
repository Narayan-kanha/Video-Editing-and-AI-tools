use pyo3::prelude::*;
use ffmpeg_next as ffmpeg;
use ffmpeg::format::Pixel;
use ffmpeg::software::scaling::{context::Context, flag::Flags};
use ffmpeg::util::frame::video::Video;
use std::path::Path;

#[pyclass]
pub struct VideoExporter {
    encoder: ffmpeg::codec::encoder::video::Encoder,
    scaler: Context,
    octx: ffmpeg::format::context::Output,
    stream_idx: usize,
    width: u32,
    height: u32,
    frame_count: i64,
}

#[pymethods]
impl VideoExporter {
    #[new]
    fn new(path: String, width: u32, height: u32, fps: i32) -> PyResult<Self> {
        ffmpeg::init().ok();
        
        let mut octx = ffmpeg::format::output(&Path::new(&path))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        let codec = ffmpeg::encoder::find(ffmpeg::codec::Id::H264).expect("H264 Not found in static build");
        let mut stream = octx.add_stream(codec).unwrap();
        let idx = stream.index();
        
        let mut encoder = ffmpeg::codec::context::Context::from_parameters(stream.parameters()).unwrap().encoder().video().unwrap();
        encoder.set_width(width);
        encoder.set_height(height);
        encoder.set_format(Pixel::YUV420P);
        encoder.set_time_base((1, fps));
        
        if octx.format().flags().contains(ffmpeg::format::flag::Flags::GLOBAL_HEADER) {
            encoder.set_flags(ffmpeg::codec::flag::Flags::GLOBAL_HEADER);
        }
        
        let encoder = encoder.open_as(codec).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        stream.set_parameters(&encoder);

        let scaler = Context::get(Pixel::RGB24, width, height, Pixel::YUV420P, width, height, Flags::BILINEAR).unwrap();
        octx.write_header().ok();

        Ok(VideoExporter {
            encoder, scaler, octx, stream_idx: idx, width, height, frame_count: 0
        })
    }

    /// Add a frame from raw RGB bytes (e.g. from Python bytes object)
    fn write_frame(&mut self, data: &[u8]) -> PyResult<()> {
        let expected = (self.width * self.height * 3) as usize;
        if data.len() != expected { return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid buffer size")); }
        
        let mut rgb = Video::new(Pixel::RGB24, self.width, self.height);
        rgb.data_mut(0).copy_from_slice(data);
        
        let mut yuv = Video::empty();
        self.scaler.run(&rgb, &mut yuv).ok();
        
        yuv.set_pts(Some(self.frame_count));
        self.frame_count += 1;
        
        self.encoder.send_frame(&yuv).ok();
        self.process_packets();
        Ok(())
    }

    fn finish(&mut self) -> PyResult<()> {
        self.encoder.send_eof().ok();
        self.process_packets();
        self.octx.write_trailer().ok();
        Ok(())
    }
}

impl VideoExporter {
    fn process_packets(&mut self) {
        let mut pkt = ffmpeg::Packet::empty();
        while self.encoder.receive_packet(&mut pkt).is_ok() {
            pkt.set_stream(self.stream_idx);
            pkt.rescale_ts(self.encoder.time_base(), self.octx.stream(self.stream_idx).unwrap().time_base());
            pkt.write_interleaved(&mut self.octx).ok();
        }
    }
}