# xauusd only windows
<img width="616" height="677" alt="image" src="https://github.com/user-attachments/assets/e554637b-7692-4424-8f3f-16d89269a3ec" />

---

### ✅ Status Konektivitas Setiap Fungsi
```
No	Fungsi	Dipanggil Oleh	Output Digunakan Oleh	Status
1	get_data()	get_closed_data()	get_closed_data()	✅
2	get_closed_data()	Main loop, trend_m5, htf, SMC	Semua analisis	✅
3	get_mt5_candle_time()	is_new_candle_mt5()	Deteksi candle	✅
4	get_last_closed_candle_time()	Main loop, is_new_candle_mt5()	Candle lock	✅
5	is_new_candle_mt5()	Main loop	new_candle → lock	✅
6	trend_m5()	Main loop	Scoring, bias	✅
7	get_higher_timeframe_trend()	Main loop	Confluence check	✅
8	engulfing()	Main loop	Scoring, dashboard	✅
9	atr_value()	get_atr_current(), patterns	ATR SL, scoring	✅
10	get_atr_current()	calculate_dynamic_sl()	SL calculation	✅
11	get_live_price()	Main loop	Bid/ask, zone check	✅
12	detect_swing_points()	detect_bos(), detect_choch()	BOS/CHoCH	✅
13	detect_bos()	Main loop	Scoring, mandatory SMC	✅
14	detect_choch()	Main loop	Scoring, mandatory SMC, bias	✅
15	calculate_atr_series()	detect_demand_zones(), detect_supply_zones()	SMC zones	✅
16	detect_demand_zones()	Initialization, update SMC	Zone detection	✅
17	detect_supply_zones()	Initialization, update SMC	Zone detection	✅
18	price_in_smc_zone()	Main loop (zone check)	in_demand_zone, in_supply_zone	✅
19	lock_zones_at_candle_close()	Main loop (new_candle)	Lock zones	✅
20	get_zone_check_price()	Main loop (new_candle)	Zone check price	✅
21	smart_liquidity_sweep()	Main loop	Scoring	✅
22	fake_breakout_filter()	Main loop	Scoring	✅
23	detect_pinbar()	Main loop / scoring	Dashboard, scoring	✅
24	detect_rejection_wick()	Main loop / scoring	Dashboard, scoring	✅
25	detect_order_block()	Main loop / scoring	Dashboard, scoring	✅
26	detect_fvg()	Main loop / scoring	Dashboard, scoring	✅
27	check_daily_loss()	Main loop	Daily loss limit	✅
28	calculate_lot()	open_trade()	Lot size	✅
29	calculate_dynamic_sl()	open_trade(), update_existing_positions_sl()	SL points	✅
30	update_existing_positions_sl()	Initialization, main loop	Update SL existing positions	✅
31	open_trade()	Main loop (entry)	Execute trade	✅
32	manage_trailing_sl()	Main loop	Update SL (trailing)	✅
33	manage_break_even()	Main loop	Update SL (BE)	✅
34	_minutes()	_in_time_range()	Session detection	✅
35	_in_time_range()	detect_sessions()	Session detection	✅
36	detect_sessions()	in_session(), get_session_status_text()	Session status	✅
37	in_session()	Main loop	session_ok	✅
38	get_session_status_text()	Main loop	Dashboard session display	✅
39	update_market_bias()	Main loop	current_bias	✅
40	calculate_signal_score()	Main loop	buy_score, sell_score	✅
41	check_mandatory_smc()	Main loop	Entry filter	✅
42	check_confluence()	Main loop	Entry filter	✅
43	render_rich_dashboard()	Main loop (live.update)	Dashboard display	✅
44	runtime_message()	Seluruh script	Dashboard event display	✅
```

---

### 📊 Diagram Alur Script

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MAIN LOOP                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. get_closed_data(TIMEFRAME_ENTRY)  ──────► df (data closed candle)     │
│                    │                                                        │
│                    ▼                                                        │
│  2. get_live_price() ──────────────────────► bid, ask (harga live)         │
│                    │                                                        │
│                    ▼                                                        │
│  3. is_new_candle_mt5(TIMEFRAME_ENTRY) ────► new_candle (deteksi candle)  │
│         │                                                                   │
│         ├── get_mt5_candle_time()                                          │
│         └── get_last_closed_candle_time()                                  │
│                    │                                                        │
│                    ▼                                                        │
│  4. in_session() ──────────────────────────► session_ok                   │
│         │                                                                   │
│         ├── detect_sessions()                                              │
│         ├── _in_time_range()                                               │
│         └── _minutes()                                                     │
│                    │                                                        │
│                    ▼                                                        │
│  5. trend_m5() ─────────────────────────────► trend (BULLISH/BEARISH)     │
│                    │                                                        │
│                    ▼                                                        │
│  6. get_higher_timeframe_trend() ───────────► htf_trend                   │
│                    │                                                        │
│                    ▼                                                        │
│  7. engulfing(df, "BUY"/"SELL") ────────────► engulf_buy / engulf_sell   │
│                    │                                                        │
│                    ▼                                                        │
│  8. detect_pinbar(df) ──────────────────────► pinbar_status               │
│  9. detect_rejection_wick(df) ──────────────► wick_status                 │
│ 10. detect_order_block(df) ──────────────────► ob_status                   │
│ 11. detect_fvg(df) ──────────────────────────► fvg_status                  │
│                    │                                                        │
│                    ▼                                                        │
│ 12. atr_value(df) ──────────────────────────► atr_val / atr_ok            │
│                    │                                                        │
│                    ▼                                                        │
│ 13. detect_bos(df, BOS_LOOKBACK) ───────────► bos                         │
│         │                                                                   │
│         └── detect_swing_points()                                          │
│                    │                                                        │
│                    ▼                                                        │
│ 14. detect_choch(df) ───────────────────────► choch                       │
│         │                                                                   │
│         └── detect_swing_points()                                          │
│                    │                                                        │
│                    ▼                                                        │
│ 15. update_market_bias(choch, trend) ───────► current_bias                │
│                    │                                                        │
│                    ▼                                                        │
│ 16. SMC ZONES (ZONE LOCK)                                                  │
│     ├── lock_zones_at_candle_close() ──────► locked_demand_zones          │
│     ├── get_zone_check_price() ─────────────► zone_check_price             │
│     └── price_in_smc_zone() ────────────────► in_demand_zone / in_supply_zone│
│                    │                                                        │
│                    ▼                                                        │
│ 17. smart_liquidity_sweep(df, "BUY"/"SELL") ─► smart_sweep_buy/sell       │
│                    │                                                        │
│                    ▼                                                        │
│ 18. fake_breakout_filter(df) ───────────────► fakeout                     │
│                    │                                                        │
│                    ▼                                                        │
│ 19. calculate_signal_score("BUY", base_conditions, df)                    │
│                    │                                                        │
│                    ├── buy_score / sell_score                              │
│                    ├── buy_met / sell_met                                  │
│                    └── met_conditions (untuk dashboard)                    │
│                    │                                                        │
│                    ▼                                                        │
│ 20. check_mandatory_smc() ──────────────────► mandatory_buy_ok/sell_ok   │
│                    │                                                        │
│                    ▼                                                        │
│ 21. check_confluence() ─────────────────────► confluence_buy/sell         │
│                    │                                                        │
│                    ▼                                                        │
│ 22. CLOSED CANDLE LOCK                                                     │
│     └── Jika new_candle dan buy_ready/sell_ready                         │
│         └── LOCK signal (locked_signal, locked_buy_score, dll)            │
│                    │                                                        │
│                    ▼                                                        │
│ 23. ENTRY EXECUTION                                                        │
│     └── Jika is_locked dan locked_signal                                  │
│         ├── calculate_dynamic_sl() ────────► sl_points                    │
│         ├── calculate_lot(sl_points) ──────► lot                          │
│         └── open_trade(direction) ─────────► Entry order                  │
│                    │                                                        │
│                    ▼                                                        │
│ 24. POSITION MANAGEMENT                                                    │
│     ├── manage_trailing_sl() ──────────────► Update SL (trailing)         │
│     └── manage_break_even() ───────────────► Update SL (BE)               │
│                    │                                                        │
│                    ▼                                                        │
│ 25. DASHBOARD                                                              │
│     └── render_rich_dashboard() ───────────► Tampilan terminal            │
│                    │                                                        │
│                    ▼                                                        │
│ 26. SMC ZONE UPDATE (setiap 60 detik)                                     │
│     ├── get_closed_data(TIMEFRAME_SMC)                                    │
│     ├── detect_demand_zones()                                             │
│     └── detect_supply_zones()                                             │
│                    │                                                        │
│                    ▼                                                        │
│ 27. ATR SL UPDATE (setiap 60 detik)                                       │
│     └── update_existing_positions_sl()                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
