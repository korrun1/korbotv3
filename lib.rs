//! 🦀 KorBot X Enhanced - Rust Core
//! Version: 2.0
//! Date: 2026-02-16
//! 
//! High-performance technical indicators and pattern recognition in Rust

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use numpy::{PyArray1, PyReadonlyArray1};
use rayon::prelude::*;

// ============================================================================
// TECHNICAL INDICATORS
// ============================================================================

/// Calculate Simple Moving Average (SMA)
/// 
/// # Arguments
/// * `data` - Price data
/// * `period` - Period for SMA
/// 
/// # Returns
/// * Vector of SMA values
#[pyfunction]
fn calculate_sma(data: PyReadonlyArray1<f64>, period: usize) -> Vec<f64> {
    let data = data.as_slice().unwrap();
    let mut sma = Vec::with_capacity(data.len());
    
    for i in 0..data.len() {
        if i < period - 1 {
            sma.push(f64::NAN);
        } else {
            let sum: f64 = data[i - period + 1..=i].iter().sum();
            sma.push(sum / period as f64);
        }
    }
    
    sma
}

/// Calculate Exponential Moving Average (EMA)
/// 
/// # Arguments
/// * `data` - Price data
/// * `period` - Period for EMA
/// 
/// # Returns
/// * Vector of EMA values
#[pyfunction]
fn calculate_ema(data: PyReadonlyArray1<f64>, period: usize) -> Vec<f64> {
    let data = data.as_slice().unwrap();
    let mut ema = Vec::with_capacity(data.len());
    
    let multiplier = 2.0 / (period as f64 + 1.0);
    
    // First EMA is SMA
    let mut current_ema = data[..period].iter().sum::<f64>() / period as f64;
    
    for i in 0..data.len() {
        if i < period {
            ema.push(f64::NAN);
        } else if i == period {
            ema.push(current_ema);
        } else {
            current_ema = (data[i] - current_ema) * multiplier + current_ema;
            ema.push(current_ema);
        }
    }
    
    ema
}

/// Calculate Relative Strength Index (RSI)
/// 
/// # Arguments
/// * `data` - Price data
/// * `period` - Period for RSI (typically 14)
/// 
/// # Returns
/// * Vector of RSI values (0-100)
#[pyfunction]
fn calculate_rsi(data: PyReadonlyArray1<f64>, period: usize) -> Vec<f64> {
    let data = data.as_slice().unwrap();
    let mut rsi = Vec::with_capacity(data.len());
    
    // Calculate price changes
    let mut gains = Vec::new();
    let mut losses = Vec::new();
    
    for i in 1..data.len() {
        let change = data[i] - data[i - 1];
        if change > 0.0 {
            gains.push(change);
            losses.push(0.0);
        } else {
            gains.push(0.0);
            losses.push(-change);
        }
    }
    
    // Calculate RSI
    rsi.push(f64::NAN); // First value is NaN
    
    for i in 0..gains.len() {
        if i < period - 1 {
            rsi.push(f64::NAN);
        } else {
            let avg_gain: f64 = gains[i - period + 1..=i].iter().sum::<f64>() / period as f64;
            let avg_loss: f64 = losses[i - period + 1..=i].iter().sum::<f64>() / period as f64;
            
            let rs = if avg_loss == 0.0 {
                100.0
            } else {
                avg_gain / avg_loss
            };
            
            let rsi_value = 100.0 - (100.0 / (1.0 + rs));
            rsi.push(rsi_value);
        }
    }
    
    rsi
}

/// Calculate Average True Range (ATR)
/// 
/// # Arguments
/// * `high` - High prices
/// * `low` - Low prices
/// * `close` - Close prices
/// * `period` - Period for ATR (typically 14)
/// 
/// # Returns
/// * Vector of ATR values
#[pyfunction]
fn calculate_atr(
    high: PyReadonlyArray1<f64>,
    low: PyReadonlyArray1<f64>,
    close: PyReadonlyArray1<f64>,
    period: usize
) -> Vec<f64> {
    let high = high.as_slice().unwrap();
    let low = low.as_slice().unwrap();
    let close = close.as_slice().unwrap();
    
    let mut atr = Vec::with_capacity(high.len());
    let mut true_ranges = Vec::new();
    
    // Calculate True Range
    atr.push(f64::NAN); // First value
    
    for i in 1..high.len() {
        let tr1 = high[i] - low[i];
        let tr2 = (high[i] - close[i - 1]).abs();
        let tr3 = (low[i] - close[i - 1]).abs();
        
        let tr = tr1.max(tr2).max(tr3);
        true_ranges.push(tr);
    }
    
    // Calculate ATR
    for i in 0..true_ranges.len() {
        if i < period - 1 {
            atr.push(f64::NAN);
        } else {
            let avg_tr: f64 = true_ranges[i - period + 1..=i].iter().sum::<f64>() / period as f64;
            atr.push(avg_tr);
        }
    }
    
    atr
}

/// Calculate MACD (Moving Average Convergence Divergence)
/// 
/// # Arguments
/// * `data` - Price data
/// * `fast_period` - Fast EMA period (typically 12)
/// * `slow_period` - Slow EMA period (typically 26)
/// * `signal_period` - Signal line period (typically 9)
/// 
/// # Returns
/// * Tuple of (MACD line, Signal line, Histogram)
#[pyfunction]
fn calculate_macd(
    py: Python,
    data: PyReadonlyArray1<f64>,
    fast_period: usize,
    slow_period: usize,
    signal_period: usize
) -> PyResult<(Py<PyArray1<f64>>, Py<PyArray1<f64>>, Py<PyArray1<f64>>)> {
    let data_slice = data.as_slice().unwrap();
    
    // Calculate EMAs
    let fast_ema = calculate_ema_internal(data_slice, fast_period);
    let slow_ema = calculate_ema_internal(data_slice, slow_period);
    
    // Calculate MACD line
    let mut macd_line: Vec<f64> = fast_ema.iter()
        .zip(slow_ema.iter())
        .map(|(f, s)| f - s)
        .collect();
    
    // Calculate signal line (EMA of MACD)
    let signal_line = calculate_ema_internal(&macd_line, signal_period);
    
    // Calculate histogram
    let histogram: Vec<f64> = macd_line.iter()
        .zip(signal_line.iter())
        .map(|(m, s)| m - s)
        .collect();
    
    Ok((
        PyArray1::from_vec(py, macd_line).to_owned(),
        PyArray1::from_vec(py, signal_line).to_owned(),
        PyArray1::from_vec(py, histogram).to_owned(),
    ))
}

/// Calculate Bollinger Bands
/// 
/// # Arguments
/// * `data` - Price data
/// * `period` - Period for moving average (typically 20)
/// * `std_dev` - Standard deviations (typically 2)
/// 
/// # Returns
/// * Tuple of (Upper band, Middle band, Lower band)
#[pyfunction]
fn calculate_bollinger_bands(
    py: Python,
    data: PyReadonlyArray1<f64>,
    period: usize,
    std_dev: f64
) -> PyResult<(Py<PyArray1<f64>>, Py<PyArray1<f64>>, Py<PyArray1<f64>>)> {
    let data = data.as_slice().unwrap();
    let mut upper = Vec::with_capacity(data.len());
    let mut middle = Vec::with_capacity(data.len());
    let mut lower = Vec::with_capacity(data.len());
    
    for i in 0..data.len() {
        if i < period - 1 {
            upper.push(f64::NAN);
            middle.push(f64::NAN);
            lower.push(f64::NAN);
        } else {
            let slice = &data[i - period + 1..=i];
            let mean: f64 = slice.iter().sum::<f64>() / period as f64;
            let variance: f64 = slice.iter()
                .map(|x| (x - mean).powi(2))
                .sum::<f64>() / period as f64;
            let std = variance.sqrt();
            
            middle.push(mean);
            upper.push(mean + std_dev * std);
            lower.push(mean - std_dev * std);
        }
    }
    
    Ok((
        PyArray1::from_vec(py, upper).to_owned(),
        PyArray1::from_vec(py, middle).to_owned(),
        PyArray1::from_vec(py, lower).to_owned(),
    ))
}

// ============================================================================
// PATTERN RECOGNITION
// ============================================================================

/// Detect bullish pin bar pattern
/// 
/// # Arguments
/// * `open` - Open prices
/// * `high` - High prices
/// * `low` - Low prices
/// * `close` - Close prices
/// 
/// # Returns
/// * Vector of boolean values indicating pattern presence
#[pyfunction]
fn detect_pin_bar(
    open: PyReadonlyArray1<f64>,
    high: PyReadonlyArray1<f64>,
    low: PyReadonlyArray1<f64>,
    close: PyReadonlyArray1<f64>
) -> Vec<bool> {
    let open = open.as_slice().unwrap();
    let high = high.as_slice().unwrap();
    let low = low.as_slice().unwrap();
    let close = close.as_slice().unwrap();
    
    let mut patterns = Vec::with_capacity(open.len());
    
    for i in 0..open.len() {
        let body = (close[i] - open[i]).abs();
        let total_range = high[i] - low[i];
        
        if total_range == 0.0 {
            patterns.push(false);
            continue;
        }
        
        // Bullish pin bar
        let lower_wick = open[i].min(close[i]) - low[i];
        let upper_wick = high[i] - open[i].max(close[i]);
        
        let is_bullish_pin = lower_wick > 2.0 * body && upper_wick < body;
        
        patterns.push(is_bullish_pin);
    }
    
    patterns
}

/// Detect engulfing pattern
/// 
/// # Arguments
/// * `open` - Open prices
/// * `close` - Close prices
/// 
/// # Returns
/// * Vector of i32: 1 for bullish, -1 for bearish, 0 for none
#[pyfunction]
fn detect_engulfing(
    open: PyReadonlyArray1<f64>,
    close: PyReadonlyArray1<f64>
) -> Vec<i32> {
    let open = open.as_slice().unwrap();
    let close = close.as_slice().unwrap();
    
    let mut patterns = Vec::with_capacity(open.len());
    patterns.push(0); // First candle
    
    for i in 1..open.len() {
        let prev_bullish = close[i-1] > open[i-1];
        let curr_bullish = close[i] > open[i];
        
        // Bullish engulfing
        if !prev_bullish && curr_bullish && 
           open[i] < close[i-1] && close[i] > open[i-1] {
            patterns.push(1);
        }
        // Bearish engulfing
        else if prev_bullish && !curr_bullish &&
                open[i] > close[i-1] && close[i] < open[i-1] {
            patterns.push(-1);
        }
        else {
            patterns.push(0);
        }
    }
    
    patterns
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/// Internal EMA calculation (returns Vec instead of PyArray)
fn calculate_ema_internal(data: &[f64], period: usize) -> Vec<f64> {
    let mut ema = Vec::with_capacity(data.len());
    let multiplier = 2.0 / (period as f64 + 1.0);
    
    let mut current_ema = data[..period].iter().sum::<f64>() / period as f64;
    
    for i in 0..data.len() {
        if i < period {
            ema.push(f64::NAN);
        } else if i == period {
            ema.push(current_ema);
        } else {
            current_ema = (data[i] - current_ema) * multiplier + current_ema;
            ema.push(current_ema);
        }
    }
    
    ema
}

/// Parallel processing example for large datasets
#[pyfunction]
fn calculate_multiple_emas_parallel(
    py: Python,
    data: PyReadonlyArray1<f64>,
    periods: Vec<usize>
) -> PyResult<Vec<Py<PyArray1<f64>>>> {
    let data_vec = data.to_vec().unwrap();
    
    let results: Vec<Vec<f64>> = periods.par_iter()
        .map(|&period| calculate_ema_internal(&data_vec, period))
        .collect();
    
    Ok(results.into_iter()
        .map(|v| PyArray1::from_vec(py, v).to_owned())
        .collect())
}

// ============================================================================
// PYTHON MODULE
// ============================================================================

/// KorBot Rust Core Module
#[pymodule]
fn korbot_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_sma, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_ema, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_rsi, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_atr, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_macd, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_bollinger_bands, m)?)?;
    m.add_function(wrap_pyfunction!(detect_pin_bar, m)?)?;
    m.add_function(wrap_pyfunction!(detect_engulfing, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_multiple_emas_parallel, m)?)?;
    
    Ok(())
}

// ============================================================================
// TESTS
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_sma() {
        let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let result = calculate_sma_internal(&data, 3);
        
        assert!(result[0].is_nan());
        assert!(result[1].is_nan());
        assert_eq!(result[2], 2.0);
        assert_eq!(result[3], 3.0);
        assert_eq!(result[4], 4.0);
    }
    
    fn calculate_sma_internal(data: &[f64], period: usize) -> Vec<f64> {
        let mut sma = Vec::with_capacity(data.len());
        
        for i in 0..data.len() {
            if i < period - 1 {
                sma.push(f64::NAN);
            } else {
                let sum: f64 = data[i - period + 1..=i].iter().sum();
                sma.push(sum / period as f64);
            }
        }
        
        sma
    }
}
