// ============================================================
// GOLD SNIPER V2.0 - FREE Edition
// ============================================================
// 100% FREE - No paid indicators required!
// Advanced Multi-Indicator + Smart Money Concepts (SMC)
// Designed for XAUUSD (Gold) on 15-Minute Timeframe
//
// Built-in Indicators (ALL FREE):
//   1. EMA Crossover (9/21) + EMA 200 Trend Bias
//   2. Supertrend (ATR-based) Trend Filter
//   3. RSI (14) + Divergence Detection
//   4. MACD (12/26/9) Momentum
//   5. ATR (14) Dynamic SL/TP Calculation
//   6. Bollinger Bands Squeeze Detection
//   7. Volume Filter
//
// Built-in Smart Money Concepts (SMC) - Coded from scratch:
//   8. Order Blocks (OB) Detection
//   9. Fair Value Gaps (FVG) Detection
//  10. Break of Structure (BOS) / Change of Character (CHoCH)
//  11. Swing High/Low Structure
//
// Session Filter:
//  12. London & New York Kill Zones
//
// Sends ALL data via single Webhook to the bot.
// ============================================================

//@version=5
indicator("GOLD SNIPER V2.0 [FREE]", overlay=true, max_labels_count=500, max_lines_count=500, max_boxes_count=500)

// ============================================================
// INPUTS
// ============================================================

// --- Webhook ---
i_secret = input.string("gold_sniper_v2_secret", "Webhook Secret", group="🔑 Webhook")

// --- EMA Settings ---
i_ema_fast   = input.int(9,   "EMA Fast",   minval=1, group="📈 EMA")
i_ema_slow   = input.int(21,  "EMA Slow",   minval=1, group="📈 EMA")
i_ema_trend  = input.int(200, "EMA Trend",  minval=1, group="📈 EMA")

// --- Supertrend ---
i_st_atr     = input.int(10,  "ATR Length", minval=1, group="🔥 Supertrend")
i_st_factor  = input.float(3.0, "Factor", minval=0.1, step=0.1, group="🔥 Supertrend")

// --- RSI ---
i_rsi_len    = input.int(14,  "RSI Length",    minval=1, group="📊 RSI")
i_rsi_ob     = input.int(70,  "Overbought",   group="📊 RSI")
i_rsi_os     = input.int(30,  "Oversold",     group="📊 RSI")
i_rsi_div    = input.bool(true, "Detect Divergence", group="📊 RSI")

// --- MACD ---
i_macd_fast  = input.int(12,  "Fast",   minval=1, group="📉 MACD")
i_macd_slow  = input.int(26,  "Slow",   minval=1, group="📉 MACD")
i_macd_sig   = input.int(9,   "Signal", minval=1, group="📉 MACD")

// --- ATR ---
i_atr_len    = input.int(14,  "ATR Length", minval=1, group="📐 ATR / SL-TP")
i_sl_mult    = input.float(1.5, "SL Multiplier", step=0.1, group="📐 ATR / SL-TP")
i_tp1_mult   = input.float(1.0, "TP1 Multiplier", step=0.1, group="📐 ATR / SL-TP")
i_tp2_mult   = input.float(2.0, "TP2 Multiplier", step=0.1, group="📐 ATR / SL-TP")
i_tp3_mult   = input.float(3.0, "TP3 Multiplier", step=0.1, group="📐 ATR / SL-TP")

// --- Bollinger Bands ---
i_bb_len     = input.int(20,  "BB Length", minval=1, group="🎯 Bollinger Bands")
i_bb_mult    = input.float(2.0, "BB Multiplier", step=0.1, group="🎯 Bollinger Bands")

// --- SMC Settings ---
i_swing_len  = input.int(5, "Swing Detection Length", minval=2, maxval=20, group="🏦 Smart Money (SMC)")
i_ob_lookback = input.int(20, "Order Block Lookback", minval=5, maxval=50, group="🏦 Smart Money (SMC)")
i_show_ob    = input.bool(true, "Show Order Blocks", group="🏦 Smart Money (SMC)")
i_show_fvg   = input.bool(true, "Show Fair Value Gaps", group="🏦 Smart Money (SMC)")
i_show_bos   = input.bool(true, "Show BOS/CHoCH", group="🏦 Smart Money (SMC)")

// --- Session Filter ---
i_session_filter = input.bool(true, "Enable Session Filter", group="🕐 Sessions")
i_london_start   = input.int(8, "London Start (UTC)", group="🕐 Sessions")
i_london_end     = input.int(16, "London End (UTC)", group="🕐 Sessions")
i_ny_start       = input.int(13, "New York Start (UTC)", group="🕐 Sessions")
i_ny_end         = input.int(21, "New York End (UTC)", group="🕐 Sessions")

// --- Signal Filters ---
i_min_body   = input.float(0.30, "Min Body/Range Ratio", minval=0.1, maxval=1.0, step=0.05, group="⚙️ Filters")
i_cooldown   = input.int(5, "Cooldown Bars", minval=1, group="⚙️ Filters")

// --- Display ---
i_show_ema   = input.bool(true,  "Show EMAs",       group="🎨 Display")
i_show_st    = input.bool(true,  "Show Supertrend", group="🎨 Display")
i_show_bb    = input.bool(false, "Show Bollinger Bands", group="🎨 Display")
i_show_levels = input.bool(true, "Show SL/TP Lines", group="🎨 Display")
i_show_table = input.bool(true,  "Show Info Table", group="🎨 Display")

// ============================================================
// 1. EMA CALCULATIONS
// ============================================================
ema_f = ta.ema(close, i_ema_fast)
ema_s = ta.ema(close, i_ema_slow)
ema_t = ta.ema(close, i_ema_trend)

ema_bull_cross = ta.crossover(ema_f, ema_s)
ema_bear_cross = ta.crossunder(ema_f, ema_s)

// ============================================================
// 2. SUPERTREND
// ============================================================
[st_val, st_dir] = ta.supertrend(i_st_factor, i_st_atr)
st_bull = st_dir < 0
st_bear = st_dir > 0

// ============================================================
// 3. RSI + DIVERGENCE
// ============================================================
rsi = ta.rsi(close, i_rsi_len)

// RSI Divergence Detection
rsi_higher = rsi > ta.valuewhen(ta.pivotlow(rsi, 5, 5), rsi, 0)
price_lower = low < ta.valuewhen(ta.pivotlow(low, 5, 5), low, 0)
bull_div = price_lower and rsi_higher and rsi < 40  // Bullish divergence

rsi_lower = rsi < ta.valuewhen(ta.pivothigh(rsi, 5, 5), rsi, 0)
price_higher = high > ta.valuewhen(ta.pivothigh(high, 5, 5), high, 0)
bear_div = price_higher and rsi_lower and rsi > 60  // Bearish divergence

// ============================================================
// 4. MACD
// ============================================================
[macd_line, sig_line, macd_hist] = ta.macd(close, i_macd_fast, i_macd_slow, i_macd_sig)

// ============================================================
// 5. ATR
// ============================================================
atr = ta.atr(i_atr_len)

// ============================================================
// 6. BOLLINGER BANDS
// ============================================================
[bb_mid, bb_up, bb_dn] = ta.bb(close, i_bb_len, i_bb_mult)
bb_width = (bb_up - bb_dn) / bb_mid * 100
bb_squeeze = bb_width < ta.sma(bb_width, 20) * 0.75

// ============================================================
// 7. VOLUME
// ============================================================
vol_sma = ta.sma(volume, 20)
vol_high = volume > vol_sma * 1.2

// ============================================================
// 8. SMART MONEY - SWING STRUCTURE
// ============================================================
swing_high = ta.pivothigh(high, i_swing_len, i_swing_len)
swing_low  = ta.pivotlow(low, i_swing_len, i_swing_len)

var float last_sh = na
var float last_sl_price = na
var float prev_sh = na
var float prev_sl_price = na

if not na(swing_high)
    prev_sh := last_sh
    last_sh := swing_high

if not na(swing_low)
    prev_sl_price := last_sl_price
    last_sl_price := swing_low

// ============================================================
// 9. SMART MONEY - BREAK OF STRUCTURE (BOS) / CHoCH
// ============================================================
var string market_structure = "NONE"
var string bos_signal = "none"

// Bullish BOS: price breaks above last swing high
bull_bos = not na(last_sh) and close > last_sh and close[1] <= last_sh
// Bearish BOS: price breaks below last swing low
bear_bos = not na(last_sl_price) and close < last_sl_price and close[1] >= last_sl_price

// CHoCH: structure change (was bearish, now bullish or vice versa)
bull_choch = bull_bos and market_structure == "BEARISH"
bear_choch = bear_bos and market_structure == "BULLISH"

if bull_bos
    market_structure := "BULLISH"
    bos_signal := bull_choch ? "bullish_choch" : "bullish_bos"
else if bear_bos
    market_structure := "BEARISH"
    bos_signal := bear_choch ? "bearish_choch" : "bearish_bos"
else
    bos_signal := "none"

// ============================================================
// 10. SMART MONEY - ORDER BLOCKS (OB)
// ============================================================
// Bullish OB: Last bearish candle before a strong bullish move
// Bearish OB: Last bullish candle before a strong bearish move

var float ob_bull_high = na
var float ob_bull_low = na
var float ob_bear_high = na
var float ob_bear_low = na
var string ob_type = "none"

// Detect Bullish Order Block
// Look for: bearish candle followed by strong bullish candle that breaks structure
is_bearish_candle_prev = close[2] < open[2]
is_strong_bull_candle = close[1] > open[1] and (close[1] - open[1]) > atr[1] * 0.5
bull_ob_detected = is_bearish_candle_prev and is_strong_bull_candle and close > high[1]

if bull_ob_detected
    ob_bull_high := high[2]
    ob_bull_low := low[2]
    ob_type := "bullish"

// Detect Bearish Order Block
is_bullish_candle_prev = close[2] > open[2]
is_strong_bear_candle = close[1] < open[1] and (open[1] - close[1]) > atr[1] * 0.5
bear_ob_detected = is_bullish_candle_prev and is_strong_bear_candle and close < low[1]

if bear_ob_detected
    ob_bear_high := high[2]
    ob_bear_low := low[2]
    ob_type := "bearish"

// Check if price is near an Order Block
price_near_bull_ob = not na(ob_bull_low) and low <= ob_bull_high and close >= ob_bull_low
price_near_bear_ob = not na(ob_bear_high) and high >= ob_bear_low and close <= ob_bear_high

// ============================================================
// 11. SMART MONEY - FAIR VALUE GAPS (FVG)
// ============================================================
var float fvg_bull_high = na
var float fvg_bull_low = na
var float fvg_bear_high = na
var float fvg_bear_low = na
var string fvg_type = "none"

// Bullish FVG: gap between candle[2] high and candle[0] low (3-candle pattern)
bull_fvg = low > high[2] and close[1] > open[1]  // Gap up with bullish middle candle
if bull_fvg
    fvg_bull_high := low
    fvg_bull_low := high[2]
    fvg_type := "bullish"

// Bearish FVG: gap between candle[0] high and candle[2] low
bear_fvg = high < low[2] and close[1] < open[1]  // Gap down with bearish middle candle
if bear_fvg
    fvg_bear_high := low[2]
    fvg_bear_low := high
    fvg_type := "bearish"

// Check if price is inside FVG
price_in_bull_fvg = not na(fvg_bull_low) and close >= fvg_bull_low and close <= fvg_bull_high
price_in_bear_fvg = not na(fvg_bear_low) and close >= fvg_bear_low and close <= fvg_bear_high

// ============================================================
// 12. SESSION FILTER
// ============================================================
utc_hour = hour(time, "UTC")
in_london = utc_hour >= i_london_start and utc_hour < i_london_end
in_ny = utc_hour >= i_ny_start and utc_hour < i_ny_end
in_session = not i_session_filter or in_london or in_ny

// Kill zone (overlap)
in_kill_zone = utc_hour >= 13 and utc_hour < 16  // London/NY overlap

// ============================================================
// CANDLE ANALYSIS
// ============================================================
body = math.abs(close - open)
range_hl = high - low
body_ratio = range_hl > 0 ? body / range_hl : 0
strong_candle = body_ratio >= i_min_body

// ============================================================
// SIGNAL GENERATION - COMBINED STRATEGY
// ============================================================
var int bars_since = 999
bars_since := bars_since + 1

// ═══════════════════════════════════════
// BUY CONDITIONS (All must align)
// ═══════════════════════════════════════
// Core: EMA crossover or EMA fast > slow
buy_ema = ema_bull_cross or (ema_f > ema_s and ema_f[1] > ema_s[1] and close > ema_f)
// Trend: Supertrend bullish
buy_st = st_bull
// Momentum: RSI not overbought + MACD positive or rising
buy_rsi = rsi < i_rsi_ob and rsi > 25
buy_macd = macd_hist > 0 or (macd_hist > macd_hist[1] and macd_hist > macd_hist[2])
// Candle: Bullish and strong
buy_candle = strong_candle and close > open
// Session
buy_session = in_session
// Cooldown
buy_cooldown = bars_since > i_cooldown

// SMC Confluence (bonus, not required but strengthens signal)
buy_smc = price_near_bull_ob or price_in_bull_fvg or bos_signal == "bullish_bos" or bos_signal == "bullish_choch"

// FINAL BUY SIGNAL
buy_signal = buy_ema and buy_st and buy_rsi and buy_macd and buy_candle and buy_session and buy_cooldown

// ═══════════════════════════════════════
// SELL CONDITIONS (All must align)
// ═══════════════════════════════════════
sell_ema = ema_bear_cross or (ema_f < ema_s and ema_f[1] < ema_s[1] and close < ema_f)
sell_st = st_bear
sell_rsi = rsi > i_rsi_os and rsi < 75
sell_macd = macd_hist < 0 or (macd_hist < macd_hist[1] and macd_hist < macd_hist[2])
sell_candle = strong_candle and close < open
sell_session = in_session
sell_cooldown = bars_since > i_cooldown

sell_smc = price_near_bear_ob or price_in_bear_fvg or bos_signal == "bearish_bos" or bos_signal == "bearish_choch"

// FINAL SELL SIGNAL
sell_signal = sell_ema and sell_st and sell_rsi and sell_macd and sell_candle and sell_session and sell_cooldown

// Reset cooldown
if buy_signal or sell_signal
    bars_since := 0

// ============================================================
// CONFIDENCE SCORE CALCULATION
// ============================================================
var float confidence = 0.0

if buy_signal
    confidence := 2.0  // Base (EMA + ST + RSI + MACD + Candle)
    confidence += close > ema_t ? 1.5 : 0.0  // Above EMA 200
    confidence += buy_smc ? 2.5 : 0.0  // SMC confluence
    confidence += (i_rsi_div and bull_div) ? 1.5 : 0.0  // RSI divergence
    confidence += in_kill_zone ? 1.0 : 0.0  // Kill zone bonus
    confidence += vol_high ? 0.5 : 0.0  // Volume bonus
    confidence += bb_squeeze ? 1.0 : 0.0  // BB squeeze bonus
    confidence := math.min(confidence, 10.0)

if sell_signal
    confidence := 2.0
    confidence += close < ema_t ? 1.5 : 0.0
    confidence += sell_smc ? 2.5 : 0.0
    confidence += (i_rsi_div and bear_div) ? 1.5 : 0.0
    confidence += in_kill_zone ? 1.0 : 0.0
    confidence += vol_high ? 0.5 : 0.0
    confidence += bb_squeeze ? 1.0 : 0.0
    confidence := math.min(confidence, 10.0)

// ============================================================
// SL / TP LEVELS
// ============================================================
buy_sl  = close - atr * i_sl_mult
buy_tp1 = close + atr * i_tp1_mult
buy_tp2 = close + atr * i_tp2_mult
buy_tp3 = close + atr * i_tp3_mult

sell_sl  = close + atr * i_sl_mult
sell_tp1 = close - atr * i_tp1_mult
sell_tp2 = close - atr * i_tp2_mult
sell_tp3 = close - atr * i_tp3_mult

// ============================================================
// PLOTTING
// ============================================================

// EMAs
plot(i_show_ema ? ema_f : na, "EMA Fast",  color=color.new(#2196F3, 0), linewidth=1)
plot(i_show_ema ? ema_s : na, "EMA Slow",  color=color.new(#FF9800, 0), linewidth=1)
plot(i_show_ema ? ema_t : na, "EMA 200",   color=color.new(#FFFFFF, 40), linewidth=2)

// Supertrend
st_color = st_bull ? color.new(#00E676, 20) : color.new(#FF1744, 20)
plot(i_show_st ? st_val : na, "Supertrend", color=st_color, linewidth=2, style=plot.style_linebr)

// Bollinger Bands
plot(i_show_bb ? bb_up : na, "BB Upper", color=color.new(color.gray, 60))
plot(i_show_bb ? bb_dn : na, "BB Lower", color=color.new(color.gray, 60))

// --- SMC Visuals ---

// Order Blocks (boxes)
if i_show_ob and bull_ob_detected
    box.new(bar_index - 2, ob_bull_high, bar_index + 10, ob_bull_low, 
         bgcolor=color.new(#00E676, 85), border_color=color.new(#00E676, 50), border_width=1)

if i_show_ob and bear_ob_detected
    box.new(bar_index - 2, ob_bear_high, bar_index + 10, ob_bear_low, 
         bgcolor=color.new(#FF1744, 85), border_color=color.new(#FF1744, 50), border_width=1)

// FVG (boxes)
if i_show_fvg and bull_fvg
    box.new(bar_index - 1, fvg_bull_high, bar_index + 8, fvg_bull_low, 
         bgcolor=color.new(#00BCD4, 88), border_color=color.new(#00BCD4, 60), border_width=1, border_style=line.style_dashed)

if i_show_fvg and bear_fvg
    box.new(bar_index - 1, fvg_bear_high, bar_index + 8, fvg_bear_low, 
         bgcolor=color.new(#E040FB, 88), border_color=color.new(#E040FB, 60), border_width=1, border_style=line.style_dashed)

// BOS / CHoCH labels
if i_show_bos and bull_bos
    lbl_text = bull_choch ? "CHoCH ▲" : "BOS ▲"
    lbl_color = bull_choch ? color.new(#FFD600, 0) : color.new(#00E676, 0)
    label.new(bar_index, low, lbl_text, style=label.style_label_up, color=lbl_color, textcolor=color.white, size=size.tiny)

if i_show_bos and bear_bos
    lbl_text = bear_choch ? "CHoCH ▼" : "BOS ▼"
    lbl_color = bear_choch ? color.new(#FFD600, 0) : color.new(#FF1744, 0)
    label.new(bar_index, high, lbl_text, style=label.style_label_down, color=lbl_color, textcolor=color.white, size=size.tiny)

// Swing Points
plotshape(not na(swing_high), "Swing High", shape.triangledown, location.abovebar, color=color.new(#FF5252, 30), size=size.tiny)
plotshape(not na(swing_low), "Swing Low", shape.triangleup, location.belowbar, color=color.new(#69F0AE, 30), size=size.tiny)

// --- Signal Labels + SL/TP Lines ---
if buy_signal
    label.new(bar_index, low, "BUY\n" + str.tostring(confidence, "#.#"), style=label.style_label_up, color=#00E676, textcolor=color.white, size=size.normal)
    if i_show_levels
        line.new(bar_index, buy_sl, bar_index + 25, buy_sl, color=color.red, style=line.style_dashed, width=1)
        label.new(bar_index + 25, buy_sl, "SL " + str.tostring(buy_sl, "#.##"), style=label.style_label_left, color=color.red, textcolor=color.white, size=size.tiny)
        line.new(bar_index, buy_tp1, bar_index + 25, buy_tp1, color=#00E676, style=line.style_dashed, width=1)
        label.new(bar_index + 25, buy_tp1, "TP1 " + str.tostring(buy_tp1, "#.##"), style=label.style_label_left, color=#00E676, textcolor=color.white, size=size.tiny)
        line.new(bar_index, buy_tp2, bar_index + 25, buy_tp2, color=#00BCD4, style=line.style_dashed, width=1)
        label.new(bar_index + 25, buy_tp2, "TP2 " + str.tostring(buy_tp2, "#.##"), style=label.style_label_left, color=#00BCD4, textcolor=color.white, size=size.tiny)
        line.new(bar_index, buy_tp3, bar_index + 25, buy_tp3, color=#2196F3, style=line.style_dashed, width=1)
        label.new(bar_index + 25, buy_tp3, "TP3 " + str.tostring(buy_tp3, "#.##"), style=label.style_label_left, color=#2196F3, textcolor=color.white, size=size.tiny)

if sell_signal
    label.new(bar_index, high, "SELL\n" + str.tostring(confidence, "#.#"), style=label.style_label_down, color=#FF1744, textcolor=color.white, size=size.normal)
    if i_show_levels
        line.new(bar_index, sell_sl, bar_index + 25, sell_sl, color=color.red, style=line.style_dashed, width=1)
        label.new(bar_index + 25, sell_sl, "SL " + str.tostring(sell_sl, "#.##"), style=label.style_label_left, color=color.red, textcolor=color.white, size=size.tiny)
        line.new(bar_index, sell_tp1, bar_index + 25, sell_tp1, color=#00E676, style=line.style_dashed, width=1)
        label.new(bar_index + 25, sell_tp1, "TP1 " + str.tostring(sell_tp1, "#.##"), style=label.style_label_left, color=#00E676, textcolor=color.white, size=size.tiny)
        line.new(bar_index, sell_tp2, bar_index + 25, sell_tp2, color=#00BCD4, style=line.style_dashed, width=1)
        label.new(bar_index + 25, sell_tp2, "TP2 " + str.tostring(sell_tp2, "#.##"), style=label.style_label_left, color=#00BCD4, textcolor=color.white, size=size.tiny)
        line.new(bar_index, sell_tp3, bar_index + 25, sell_tp3, color=#2196F3, style=line.style_dashed, width=1)
        label.new(bar_index + 25, sell_tp3, "TP3 " + str.tostring(sell_tp3, "#.##"), style=label.style_label_left, color=#2196F3, textcolor=color.white, size=size.tiny)

// Background
bgcolor(buy_signal ? color.new(#00E676, 92) : sell_signal ? color.new(#FF1744, 92) : na)

// BB Squeeze dots
plotshape(bb_squeeze, "BB Squeeze", shape.diamond, location.bottom, color=color.new(#FFD600, 30), size=size.tiny)

// RSI Divergence markers
plotshape(i_rsi_div and bull_div, "Bull Divergence", shape.circle, location.belowbar, color=color.new(#00E676, 20), size=size.tiny)
plotshape(i_rsi_div and bear_div, "Bear Divergence", shape.circle, location.abovebar, color=color.new(#FF1744, 20), size=size.tiny)

// Session background
bgcolor(i_session_filter and in_kill_zone ? color.new(#FFD600, 95) : na, title="Kill Zone")

// ============================================================
// WEBHOOK ALERTS
// ============================================================

// Build SMC data strings
ob_type_str = price_near_bull_ob ? "bullish" : price_near_bear_ob ? "bearish" : "none"
fvg_type_str = price_in_bull_fvg ? "bullish" : price_in_bear_fvg ? "bearish" : "none"
st_dir_str = st_bull ? "UP" : "DOWN"
ms_str = market_structure

// BUY Alert Message
buy_msg = '{"secret":"' + i_secret + '","symbol":"XAUUSD","signal":"BUY",' +
     '"price":' + str.tostring(close) + ',' +
     '"atr":' + str.tostring(atr, "#.##") + ',' +
     '"rsi":' + str.tostring(rsi, "#.#") + ',' +
     '"macd_hist":' + str.tostring(macd_hist, "#.###") + ',' +
     '"ema_fast":' + str.tostring(ema_f, "#.##") + ',' +
     '"ema_slow":' + str.tostring(ema_s, "#.##") + ',' +
     '"ema_200":' + str.tostring(ema_t, "#.##") + ',' +
     '"supertrend":"' + st_dir_str + '",' +
     '"supertrend_value":' + str.tostring(st_val, "#.##") + ',' +
     '"ob_type":"' + ob_type_str + '",' +
     '"ob_high":' + str.tostring(nz(ob_bull_high, 0), "#.##") + ',' +
     '"ob_low":' + str.tostring(nz(ob_bull_low, 0), "#.##") + ',' +
     '"fvg_type":"' + fvg_type_str + '",' +
     '"fvg_high":' + str.tostring(nz(fvg_bull_high, 0), "#.##") + ',' +
     '"fvg_low":' + str.tostring(nz(fvg_bull_low, 0), "#.##") + ',' +
     '"bos":"' + bos_signal + '",' +
     '"market_structure":"' + ms_str + '",' +
     '"confidence":' + str.tostring(confidence, "#.#") + ',' +
     '"bb_squeeze":' + (bb_squeeze ? "true" : "false") + ',' +
     '"vol_high":' + (vol_high ? "true" : "false") + ',' +
     '"rsi_divergence":' + (bull_div ? "true" : "false") + ',' +
     '"kill_zone":' + (in_kill_zone ? "true" : "false") + ',' +
     '"high":' + str.tostring(high) + ',' +
     '"low":' + str.tostring(low) + ',' +
     '"open":' + str.tostring(open) + ',' +
     '"close":' + str.tostring(close) + ',' +
     '"volume":' + str.tostring(volume) + '}'

alertcondition(buy_signal, "Gold Sniper BUY", buy_msg)

// SELL Alert Message
sell_msg = '{"secret":"' + i_secret + '","symbol":"XAUUSD","signal":"SELL",' +
     '"price":' + str.tostring(close) + ',' +
     '"atr":' + str.tostring(atr, "#.##") + ',' +
     '"rsi":' + str.tostring(rsi, "#.#") + ',' +
     '"macd_hist":' + str.tostring(macd_hist, "#.###") + ',' +
     '"ema_fast":' + str.tostring(ema_f, "#.##") + ',' +
     '"ema_slow":' + str.tostring(ema_s, "#.##") + ',' +
     '"ema_200":' + str.tostring(ema_t, "#.##") + ',' +
     '"supertrend":"' + st_dir_str + '",' +
     '"supertrend_value":' + str.tostring(st_val, "#.##") + ',' +
     '"ob_type":"' + ob_type_str + '",' +
     '"ob_high":' + str.tostring(nz(ob_bear_high, 0), "#.##") + ',' +
     '"ob_low":' + str.tostring(nz(ob_bear_low, 0), "#.##") + ',' +
     '"fvg_type":"' + fvg_type_str + '",' +
     '"fvg_high":' + str.tostring(nz(fvg_bear_high, 0), "#.##") + ',' +
     '"fvg_low":' + str.tostring(nz(fvg_bear_low, 0), "#.##") + ',' +
     '"bos":"' + bos_signal + '",' +
     '"market_structure":"' + ms_str + '",' +
     '"confidence":' + str.tostring(confidence, "#.#") + ',' +
     '"bb_squeeze":' + (bb_squeeze ? "true" : "false") + ',' +
     '"vol_high":' + (vol_high ? "true" : "false") + ',' +
     '"rsi_divergence":' + (bear_div ? "true" : "false") + ',' +
     '"kill_zone":' + (in_kill_zone ? "true" : "false") + ',' +
     '"high":' + str.tostring(high) + ',' +
     '"low":' + str.tostring(low) + ',' +
     '"open":' + str.tostring(open) + ',' +
     '"close":' + str.tostring(close) + ',' +
     '"volume":' + str.tostring(volume) + '}'

alertcondition(sell_signal, "Gold Sniper SELL", sell_msg)

// Combined Alert
any_sig = buy_signal or sell_signal
sig_type = buy_signal ? "BUY" : "SELL"

combined_msg = buy_signal ? buy_msg : sell_msg
alertcondition(any_sig, "Gold Sniper Signal", combined_msg)

// ============================================================
// INFO TABLE
// ============================================================
if i_show_table and barstate.islast
    var table tbl = table.new(position.top_right, 2, 12, bgcolor=color.new(#1a1a2e, 10), border_width=1, border_color=color.new(#333366, 50))
    
    table.cell(tbl, 0, 0, "🥇 GOLD SNIPER V2", text_color=#FFD700, text_size=size.small, text_halign=text.align_left)
    table.cell(tbl, 1, 0, "FREE", text_color=#00E676, text_size=size.small)
    
    table.cell(tbl, 0, 1, "EMA 200 Trend", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 1, close > ema_t ? "BULL ▲" : "BEAR ▼", text_color=close > ema_t ? #00E676 : #FF1744, text_size=size.tiny)
    
    table.cell(tbl, 0, 2, "Supertrend", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 2, st_bull ? "UP ▲" : "DOWN ▼", text_color=st_bull ? #00E676 : #FF1744, text_size=size.tiny)
    
    table.cell(tbl, 0, 3, "EMA Cross", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 3, ema_f > ema_s ? "BULL ▲" : "BEAR ▼", text_color=ema_f > ema_s ? #00E676 : #FF1744, text_size=size.tiny)
    
    table.cell(tbl, 0, 4, "RSI", text_color=#AAAAAA, text_size=size.tiny)
    rsi_c = rsi > i_rsi_ob ? #FF1744 : rsi < i_rsi_os ? #00E676 : #FFFFFF
    table.cell(tbl, 1, 4, str.tostring(rsi, "#.#"), text_color=rsi_c, text_size=size.tiny)
    
    table.cell(tbl, 0, 5, "MACD", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 5, str.tostring(macd_hist, "#.##"), text_color=macd_hist > 0 ? #00E676 : #FF1744, text_size=size.tiny)
    
    table.cell(tbl, 0, 6, "ATR", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 6, str.tostring(atr, "#.##"), text_color=#FFFFFF, text_size=size.tiny)
    
    table.cell(tbl, 0, 7, "Structure", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 7, market_structure, text_color=market_structure == "BULLISH" ? #00E676 : market_structure == "BEARISH" ? #FF1744 : #AAAAAA, text_size=size.tiny)
    
    table.cell(tbl, 0, 8, "Order Block", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 8, ob_type_str != "none" ? str.upper(ob_type_str) : "—", text_color=ob_type_str == "bullish" ? #00E676 : ob_type_str == "bearish" ? #FF1744 : #AAAAAA, text_size=size.tiny)
    
    table.cell(tbl, 0, 9, "BB Squeeze", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 9, bb_squeeze ? "YES ⚡" : "NO", text_color=bb_squeeze ? #FFD600 : #AAAAAA, text_size=size.tiny)
    
    table.cell(tbl, 0, 10, "Volume", text_color=#AAAAAA, text_size=size.tiny)
    table.cell(tbl, 1, 10, vol_high ? "HIGH ▲" : "NORMAL", text_color=vol_high ? #00E676 : #AAAAAA, text_size=size.tiny)
    
    table.cell(tbl, 0, 11, "Session", text_color=#AAAAAA, text_size=size.tiny)
    sess_text = in_kill_zone ? "KILL ZONE 🔥" : in_london ? "LONDON" : in_ny ? "NEW YORK" : "OFF"
    sess_color = in_kill_zone ? #FFD600 : in_session ? #00E676 : #FF1744
    table.cell(tbl, 1, 11, sess_text, text_color=sess_color, text_size=size.tiny)
