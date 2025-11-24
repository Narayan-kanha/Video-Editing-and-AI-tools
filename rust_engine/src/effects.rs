use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::cmp::{min, max};

#[pyclass]
pub struct ImageProcessor;

#[pymethods]
impl ImageProcessor {
    
    /// FEATURE 1: OVERLAY / BLEND
    /// Mimics libopenshot::Layer
    /// Puts a foreground image (rgba) onto a background (rgb/rgba) at specific coordinates.
    /// background: Raw bytes [R, G, B, R, G, B...]
    /// foreground: Raw bytes [R, G, B, A, R, G, B, A...] (MUST HAVE ALPHA)
    #[staticmethod]
    fn overlay(
        py: Python,
        background: &[u8], 
        bg_width: usize,
        foreground: &[u8], 
        fg_width: usize,
        fg_height: usize,
        x_pos: i32, 
        y_pos: i32,
        global_opacity: f32
    ) -> PyResult<Py<PyBytes>> {
        
        // Clone background so we don't modify the original frame
        let mut canvas = background.to_vec();
        
        // Iterate over the foreground (Overlay)
        // O(N) Loop - Extremely fast in Rust compared to Python loops
        for fy in 0..fg_height {
            let abs_y = y_pos + fy as i32;
            
            // Check boundaries
            if abs_y < 0 { continue; }
            
            // Calculate Background Row start index
            // Assuming Background is RGB (3 bytes) and standard pitch
            let bg_stride = bg_width * 3;
            
            // Calculate Foreground Row start index
            // Assuming Foreground is RGBA (4 bytes)
            let fg_stride = fg_width * 4;
            
            let bg_row_idx = (abs_y as usize) * bg_stride;
            let fg_row_idx = fy * fg_stride;

            // Stop if we go off bottom of canvas
            if bg_row_idx >= canvas.len() { break; }

            for fx in 0..fg_width {
                let abs_x = x_pos + fx as i32;
                
                if abs_x < 0 { continue; }
                let bg_px_idx = bg_row_idx + (abs_x as usize * 3);
                
                // Stop if we go off right edge of canvas
                if bg_px_idx + 2 >= bg_row_idx + bg_stride { break; }

                // Get Foreground Indices (RGBA)
                let fg_px_idx = fg_row_idx + (fx * 4);
                
                let r_fg = foreground[fg_px_idx];
                let g_fg = foreground[fg_px_idx + 1];
                let b_fg = foreground[fg_px_idx + 2];
                let a_fg = foreground[fg_px_idx + 3] as f32 / 255.0; // Alpha 0.0-1.0

                // Combined Opacity
                let final_alpha = a_fg * global_opacity;
                if final_alpha <= 0.0 { continue; }

                // --- THE BLEND MATH (Standard Porter-Duff Over) ---
                let r_bg = canvas[bg_px_idx];
                let g_bg = canvas[bg_px_idx + 1];
                let b_bg = canvas[bg_px_idx + 2];

                // NewPixel = (FG * Alpha) + (BG * (1 - Alpha))
                let inv_alpha = 1.0 - final_alpha;

                canvas[bg_px_idx]     = (r_fg as f32 * final_alpha + r_bg as f32 * inv_alpha) as u8;
                canvas[bg_px_idx + 1] = (g_fg as f32 * final_alpha + g_bg as f32 * inv_alpha) as u8;
                canvas[bg_px_idx + 2] = (b_fg as f32 * final_alpha + b_bg as f32 * inv_alpha) as u8;
            }
        }
        
        Ok(PyBytes::new_bound(py, &canvas).into())
    }

    /// FEATURE 2: COLOR EFFECTS
    /// Mimics libopenshot::Color/Brightness
    /// adjusts brightness (-255 to +255) and contrast (0.0 to 5.0)
    #[staticmethod]
    fn color_adjust(
        py: Python,
        frame_bytes: &[u8],
        brightness: i16,
        contrast: f32
    ) -> PyResult<Py<PyBytes>> {
        let mut result = Vec::with_capacity(frame_bytes.len());
        
        // Pre-calc contrast factor to avoid doing math 2,000,000 times
        let factor = (259.0 * (contrast + 255.0)) / (255.0 * (259.0 - contrast));
        
        // Loop happens entirely in CPU L1 Cache (Very fast)
        for &pixel in frame_bytes {
            // 1. Brightness
            let mut val = pixel as i16 + brightness;
            
            // 2. Contrast
            if contrast != 1.0 {
                 val = (factor * (val as f32 - 128.0) + 128.0) as i16;
            }

            // 3. Clamp (Ensure 0-255)
            let clamped = if val > 255 { 255 } else if val < 0 { 0 } else { val } as u8;
            
            result.push(clamped);
        }

        Ok(PyBytes::new_bound(py, &result).into())
    }
}