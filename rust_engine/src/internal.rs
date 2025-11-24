use std::fs::File;
use std::path::Path;
use symphonia::core::codecs::{Decoder, DecoderOptions, CODEC_TYPE_NULL};
use symphonia::core::formats::{FormatOptions, FormatReader};
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

pub type AudioResult<T> = std::result::Result<T, Box<dyn std::error::Error>>;

pub struct AudioReader {
    pub format: Box<dyn FormatReader>,
    pub decoder: Box<dyn Decoder>,
    pub track_id: u32,
    pub sample_rate: u32,
    pub duration_frames: Option<u64>,
    pub channels: u32,
}

impl AudioReader {
    pub fn new(path: &str) -> AudioResult<Self> {
        let src = File::open(Path::new(path))?;
        let mss = MediaSourceStream::new(Box::new(src), Default::default());

        let mut hint = Hint::new();
        if let Some(ext) = Path::new(path).extension().and_then(|e| e.to_str()) {
            hint.with_extension(ext);
        }

        let probed = symphonia::default::get_probe()
            .format(&hint, mss, &FormatOptions::default(), &MetadataOptions::default())?;

        let format = probed.format;
        let track = format.tracks().iter().find(|t| t.codec_params.codec != CODEC_TYPE_NULL)
            .ok_or("No supported audio track found")?;

        let track_id = track.id;
        let codec_params = track.codec_params.clone();
        let sample_rate = codec_params.sample_rate.unwrap_or(44100);
        let duration_frames = codec_params.n_frames;
        let channels = codec_params.channels.map(|c| c.count() as u32).unwrap_or(2);

        let decoder = symphonia::default::get_codecs()
            .make(&codec_params, &DecoderOptions::default())?;

        Ok(Self { format, decoder, track_id, sample_rate, duration_frames, channels })
    }
}