# ⚡ Quick Start Guide

## 🚀 Get Running in 3 Minutes

### Step 1: Install Dependencies (1 minute)
```bash
pip install -r requirements.txt
```

### Step 2: Start the App (30 seconds)
```bash
streamlit run app.py
```

Your browser will automatically open to: `http://localhost:8501`

### Step 3: Upload Telemetry Data (30 seconds)
1. Click "Choose a CSV file" in the sidebar
2. Select your telemetry CSV
3. Watch the analysis appear instantly!

---

## 📊 Test with Sample Data

We've included `sample_telemetry.csv` - a realistic 5-second lap captured at high frequency.

```bash
# Already in the workspace - just upload it via the UI
sample_telemetry.csv
```

Expected results:
- ✅ Overall Score: ~75-85 (realistic driving)
- ✅ Insights: 5-7 actionable feedback items
- ✅ All visualizations generate without errors
- ✅ No warnings or crashes

---

## 📋 CSV Format Checklist

Your CSV must have AT LEAST these columns:

| Column | Type | Range | Notes |
|--------|------|-------|-------|
| time | float | 0+ | Sequential seconds |
| speed | float | 0+ | km/h |
| throttle_input | float | 0.0-1.0 | 0=off, 1=full |
| brake_input | float | 0.0-1.0 | 0=off, 1=full |
| steering_angle | float | -360 to 360 | degrees |
| combined_slip_angle | float | -90 to 90 | degrees |
| yaw_moment | float | -10 to 10 | rad/s |
| pitch | float | -90 to 90 | degrees |
| rpm | float | 0+ | engine RPM |
| gear | float | 1-10 | gear number |

**Optional columns:**
- latitude, longitude (enables track map)

---

## ✅ First Run Checklist

After uploading your CSV:

- [ ] All 6 charts load without errors
- [ ] Smoothness/Control/Efficiency scores appear
- [ ] At least 2 insights show
- [ ] No red error messages
- [ ] Data table shows your rows

If any of these fail ➜ See **Troubleshooting** section below

---

## 🎯 Understanding the Dashboard

### Top Section (Metrics)
```
Overall Score: 0-100        ← Your grade
Smoothness: 0-100          ← Input smoothness
Control: 0-100             ← Grip/stability
Aggression: 0-100          ← Speed aggressiveness
Efficiency: 0-100          ← RPM optimization
```

### Middle Section (Insights)
- ⚠️ Issues detected (oversteer, wheel spin, etc.)
- 📈 Score-based feedback
- 🏆 Performance grade

### Bottom Section (Visualizations)
Click tabs to explore:
- **Speed**: Velocity profile
- **Inputs**: Throttle/brake over time
- **Slip Angle**: Grip loss detection
- **Yaw vs Steering**: Vehicle response
- **RPM vs Gear**: Efficiency analysis
- **Problem Zones**: All issues highlighted

---

## 🔧 Customization Quick Reference

Edit thresholds in `app.py` (lines ~30-40):

```python
# Make oversteer/understeer detection more/less sensitive
STEERING_THRESHOLD = 5           # Lower = more sensitive
SLIP_ANGLE_THRESHOLD = 5         # Lower = more sensitive

# Adjust what counts as "harsh braking"
BRAKING_THRESHOLD = 0.2          # Lower = more events detected

# Change scoring weights (must sum to 1.0)
SMOOTHNESS_WEIGHT = 0.25
AGGRESSION_WEIGHT = 0.20
CONTROL_WEIGHT = 0.35            # Most important
EFFICIENCY_WEIGHT = 0.20
```

---

## 🚨 Troubleshooting

### Problem: "No such file or directory: requirements.txt"
**Solution:**
```bash
# Make sure you're in the telemetry folder
cd c:\Users\Maha\Documents\telemetry
pip install -r requirements.txt
```

### Problem: "ModuleNotFoundError: No module named 'streamlit'"
**Solution:**
```bash
pip install streamlit pandas numpy plotly
```

### Problem: CSV won't upload
**Check:**
1. ✅ File is actually a CSV (not .xlsx, .txt, etc.)
2. ✅ File encoding is UTF-8
3. ✅ Column names exactly match the format
4. ✅ No special characters in column names

**Try:**
```bash
# Convert Excel to CSV
# Open in Excel → Save As → CSV UTF-8
```

### Problem: "ValueError: could not convert string to float"
**Cause:** A numeric column has non-numeric data
**Solution:**
- Check your CSV for empty cells or text values
- Use sample_telemetry.csv as a template
- Fill empty cells with numeric values

### Problem: Charts show but no data
**Check:**
- Upload CSV first
- Wait for file to process (2-3 seconds)
- Refresh browser if stuck

### Problem: "TypeError: unsupported operand type"
**Cause:** Missing critical column in CSV
**Solution:**
- Verify your CSV has all required columns
- Use `sample_telemetry.csv` as reference
- Check spelling: `throttle_input` not `throttle`

### Problem: App crashes or freezes
**Solution:**
```bash
# Kill the app
Ctrl+C in terminal

# Clear cache
streamlit cache clear

# Restart
streamlit run app.py
```

---

## 📝 Tips for Best Results

### Data Quality
1. **Consistent sampling rate** - Don't mix 10Hz and 100Hz data
2. **Complete laps** - At least 1 full lap (~60-120 seconds)
3. **Real vehicle data** - The system is calibrated for realistic telemetry
4. **Minimal gaps** - Avoid long periods of missing data

### Getting Useful Insights
1. Upload **multiple laps** to find patterns
2. Compare **different drivers** on same track
3. Use **sample_telemetry.csv** to verify functionality first
4. Look for **repeated patterns** across laps

### Improving Your Score
- **Smoothness**: Gradual throttle/brake changes (ramp, don't snap)
- **Control**: Reduce slip angles and yaw instability
- **Efficiency**: Keep RPM in 4000-7000 range
- **Aggression**: Drive near your limit, not timidly or recklessly

---

## 🎬 Common Workflows

### Workflow 1: Analyze Single Lap
```
1. Export telemetry from your data logger
2. Ensure CSV format matches requirements
3. Upload via Streamlit
4. Review score and insights
5. Identify top improvement area
6. Note driving changes needed
```

### Workflow 2: Compare Two Laps
```
1. Upload first lap → screenshot scores/insights
2. Upload second lap → compare to first
3. Look for improvements in each metric
4. Track progress over multiple laps
```

### Workflow 3: Identify Problem Corners
```
1. Upload telemetry
2. Set visible time window for one corner
3. Look at "Problem Zones" tab
4. Identify when oversteer/understeer occurs
5. Note exact moment to improve
```

### Workflow 4: Optimize Gearing
```
1. Upload telemetry
2. Check "RPM vs Gear" chart
3. See if staying in 4000-7000 range
4. Identify shift points that are too early/late
5. Compare multiple laps with different shifts
```

---

## 📚 Documentation

- **README.md** - Full feature overview
- **TECHNICAL_DOCUMENTATION.md** - How algorithms work
- **QUICK_START.md** - This file
- **sample_telemetry.csv** - Example data to test with

---

## ❓ Common Questions

**Q: Can I analyze ACC, iRacing, or other sim data?**
A: Yes! Export to CSV with matching columns. May need to rename columns.

**Q: Does GPS data really help?**
A: Yes! Shows exactly where on track you're losing performance.

**Q: Can I use this for coaching?**
A: Absolutely! Share the generated insights with driver for feedback.

**Q: How often should I upload new laps?**
A: Every practice session to track progress over time.

**Q: Can I modify the scoring?**
A: Yes! Edit weights in app.py around line 32-36.

**Q: What if my RPM goes to 10,000+?**
A: Edit the "ideal_rpm" range in calculate_efficiency_score() function.

---

## 🎓 Learning Path

### Beginner (Get Running)
1. ✅ Install and run app
2. ✅ Upload sample data
3. ✅ Read all insights
4. ✅ Explore each chart

### Intermediate (Use Effectively)
1. ✅ Upload your own lap data
2. ✅ Understand your scores
3. ✅ Make one driving improvement
4. ✅ Re-upload and compare

### Advanced (Customize)
1. ✅ Edit detection thresholds
2. ✅ Adjust scoring weights
3. ✅ Add custom analysis functions
4. ✅ Export insights to external tools

---

## 🎉 You're Ready!

```bash
cd c:\Users\Maha\Documents\telemetry
pip install -r requirements.txt
streamlit run app.py
```

Upload `sample_telemetry.csv` first to verify everything works.

**Questions?** Check TECHNICAL_DOCUMENTATION.md or review the code comments.

**Found a bug?** The system is designed for real-world robustness - try adjusting thresholds if needed.

**Ready to improve?** Upload your telemetry and let the insights guide you! 🏁
