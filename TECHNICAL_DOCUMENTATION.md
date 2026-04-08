# 📖 Technical Documentation

## System Architecture

```
Raw CSV Data
    ↓
[Data Loading] → Load CSV with pandas
    ↓
[Data Cleaning] → Handle missing values, validate, sort
    ↓
[Feature Engineering] → Create derived metrics (acceleration, stability index, etc.)
    ↓
[Advanced Analysis] → Detect issues (oversteer, understeer, wheel spin, etc.)
    ├─ Grip Analysis
    ├─ Braking Analysis
    ├─ Throttle Analysis
    ├─ Stability Analysis
    └─ Efficiency Analysis
    ↓
[Driver Scoring] → Calculate scores (smoothness, control, aggression, efficiency)
    ↓
[Visualization] → Generate interactive Plotly charts
    ↓
[Insight Generation] → Create actionable feedback
    ↓
[Streamlit Dashboard] → Display UI with metrics, insights, graphs
```

## Detailed Algorithm Explanations

### 1. Data Cleaning Pipeline

#### Input Validation
```python
1. Check if 'time' column exists
2. If missing: create sequential time values
3. Sort all rows by time (ascending)
4. Ensure all critical columns are numeric
```

#### Missing Value Handling
```python
For each numeric column:
  1. Forward fill (propagate last known value forward)
  2. Backward fill (handle leading NaNs)
  3. This preserves data continuity while avoiding artifical interpolation
```

#### Value Clipping
```python
- throttle_input: [0.0, 1.0]
- brake_input: [0.0, 1.0]
- Other values: natural range (no hard clipping)
```

### 2. Feature Engineering

#### Acceleration
```
acceleration = speed[t] - speed[t-1]
```
Represents rate of speed change (delta per time step)

#### Slip Severity
```
slip_severity = |combined_slip_angle|
```
Absolute value of slip angle to measure grip loss magnitude

#### Stability Index
```
stability_index = |yaw_moment| / (|steering_angle| + 0.01)
```
Ratio of yaw response to steering input. 
- Low = responsive steering
- High = excessive yaw (instability)
- The +0.01 prevents division by zero

#### RPM Efficiency
```
rpm_efficiency = rpm / (gear + 0.1)
```
Normalized engine speed relative to gear selection
- Higher = higher RPM per gear
- Used to detect over-revving situations

#### Zone Detection
```
is_braking = brake_input > BRAKING_THRESHOLD (0.2)
is_throttling = throttle_input > THROTTLE_THRESHOLD (0.2)
is_cornering = |steering_angle| > STEERING_THRESHOLD (5°)
```

### 3. Grip Analysis: Oversteer vs Understeer

#### Oversteer Detection
```
CONDITION: (|yaw_moment| > 2.0 rad/s) AND (|combined_slip_angle| > 8°)

Reasoning:
- High yaw_moment: rear axle sliding out
- High slip_angle: tires losing lateral grip
- Combined: rear end is sliding more than front
→ Driver must reduce steering or throttle
```

#### Understeer Detection
```
CONDITION: (|steering_angle| > 10°) AND (|yaw_moment| < 1.0 rad/s)

Reasoning:
- High steering input: driver turning wheel aggressively
- Low yaw response: car not responding to steering
- Combined: front tires have lost grip
→ Driver must brake earlier or reduce entry speed
```

### 4. Braking Analysis

#### Harsh Braking Detection
```
CONDITION: (brake_input > 0.7) AND (|pitch| > 2°)

Reasoning:
- brake_input > 0.7: heavy brake application
- pitch > 2°: strong longitudinal compression (weight transfer)
- Combined: indicates abrupt braking causing instability
→ Modulate brake pressure more smoothly
```

### 5. Throttle Analysis

#### Wheel Spin Detection
```
CONDITION: (throttle_input > 0.7) AND (|combined_slip_angle| > 10°)

Reasoning:
- throttle_input > 0.7: aggressive acceleration
- combined_slip_angle > 10°: significant tire slip
- Combined: wheels spinning up (losing longitudinal grip)
→ Apply throttle more gradually to maintain traction
```

### 6. Stability Analysis

#### Instability Flagging
```
CONDITION: stability_index > 3.0

Meaning:
- stability_index = |yaw_moment| / |steering_angle|
- > 3.0: excessive yaw relative to steering input
→ Vehicle is unstable; need smoother inputs
```

## Scoring System (0-100)

### Smoothness Score
```
Purpose: Reward gradual, controlled inputs

Calculation:
1. throttle_variance = standard deviation of throttle_input
2. brake_variance = standard deviation of brake_input
3. throttle_score = max(0, 100 - throttle_variance * 100)
4. brake_score = max(0, 100 - brake_variance * 100)
5. smoothness_score = (throttle_score + brake_score) / 2

Interpretation:
- 80-100: Very smooth, professional-level control
- 60-80: Acceptable smoothness
- <60: Jerky, inconsistent inputs
```

### Control Score
```
Purpose: Reward maintaining vehicle grip/stability

Calculation:
1. slip_score = max(0, 100 - avg_slip_angle * 5)
2. stability_score = max(0, 100 - avg_stability_index * 10)
3. control_score = (slip_score + stability_score) / 2

Interpretation:
- 80-100: Excellent grip and stability
- 60-80: Good control, occasional slides
- <60: Frequent loss of grip
```

### Aggression Score
```
Purpose: Reward balanced aggressive inputs (not too timid, not reckless)

Calculation:
1. high_throttle_pct = (throttle > 0.8).count() / total * 100
2. high_brake_pct = (brake > 0.7).count() / total * 100
3. aggression = (high_throttle_pct + high_brake_pct) / 2
4. If aggression < 30: return 60 (too conservative)
5. If aggression > 80: return 60 (too reckless)
6. Else: return 80 (good balance)

Interpretation:
- 80-100: Perfect balance of speed and control
- 60-80: Either too timid or too aggressive
- <60: Extremely unbalanced driving
```

### Efficiency Score
```
Purpose: Reward optimal engine/gear usage

Calculation:
1. ideal_rpm_min = 4000
2. ideal_rpm_max = 7000
3. in_range_count = (rpm >= 4000 AND rpm <= 7000).count()
4. efficiency = in_range_count / total * 100

Interpretation:
- 80-100: Mostly operating in ideal RPM range
- 60-80: Frequent deviations from ideal
- <60: Poor gear selection or shift timing
```

### Final Overall Score
```
overall_score = (
    smoothness * 0.25 +
    aggression * 0.20 +
    control * 0.35 +
    efficiency * 0.20
)

Weights:
- Control (35%): Most important - safety and grip
- Smoothness (25%): Important for consistency
- Efficiency (20%): Important for lap time
- Aggression (20%): Supporting metric

Performance Grade:
- 0-60: Beginner (🔰)
- 60-85: Intermediate (📈)
- 85-100: Pro (🏆)
```

## Visualization Details

### Speed vs Time
- **Purpose**: Show velocity profile across entire lap
- **Y-axis**: Speed (km/h)
- **X-axis**: Time (seconds)
- **Use**: Identify braking zones and acceleration profiles

### Throttle & Brake vs Time
- **Purpose**: Show input behavior over lap
- **Y-axis**: Input value (0-1)
- **X-axis**: Time (seconds)
- **Use**: Identify aggressive or smooth driving

### Slip Angle vs Time
- **Purpose**: Show loss of grip throughout lap
- **Y-axis**: Slip angle (degrees)
- **X-axis**: Time (seconds)
- **Use**: Identify corner where grip is lost

### Yaw vs Steering
- **Purpose**: Show vehicle response to steering input
- **X-axis**: Steering angle (degrees)
- **Y-axis**: Yaw moment (rad/s)
- **Color**: Speed gradient
- **Use**: Identify oversteer/understeer behavior
- **Interpretation**:
  - Steep slope = responsive (good)
  - Shallow slope + high clustering = understeer
  - High scatter = unstable

### RPM vs Gear
- **Purpose**: Show gear selection efficiency
- **Y1-axis (left)**: RPM
- **Y2-axis (right)**: Gear number
- **X-axis**: Time (seconds)
- **Use**: Identify suboptimal shifting patterns

### Problem Zones
- **Purpose**: Highlight all detected issues in one graph
- **Base line**: Speed profile
- **Red X markers**: Oversteer events
- **Orange diamonds**: Understeer events
- **Yellow circles**: Instability events
- **Use**: Quick visual reference for problem areas

### Track Map (GPS)
- **Purpose**: Overlay performance on actual track
- **Color gradient**: Speed at each location
- **Bright**: High speed (straights)
- **Dark**: Low speed (corners/braking zones)
- **Use**: Spatial analysis of performance

## Insight Generation Logic

### Rules Engine
```
IF oversteer_events > 0:
    → "⚠️ Oversteer detected in X% of lap"
    
IF understeer_events > 0:
    → "⚠️ Understeer detected in X% of lap"
    
IF harsh_braking_events > 0:
    → "🛑 Harsh braking detected X times"
    
IF wheel_spin_events > 0:
    → "🔄 Wheel spin detected X times"
    
IF instability_events > 0:
    → "⚡ Vehicle instability detected in X% of lap"
    
IF smoothness_score < 70:
    → "📊 Smoothness Score is low"
    
IF control_score < 70:
    → "🎯 Control Score is low"
    
IF efficiency_score < 70:
    → "⚙️ Efficiency Score is low"
    
IF overall_score > 85:
    → "✅ Excellent performance!"
```

### Insight Specificity
Each insight includes:
- **Icon**: Quick visual identification
- **Metric**: Specific measurement (e.g., "15% of lap")
- **Action**: Clear recommendation (e.g., "reduce steering")
- **Context**: Specific scenario (e.g., "high-speed corners")

## Performance Optimization

### Computational Complexity
- Data loading: O(n) where n = number of data points
- Cleaning: O(n)
- Feature engineering: O(n)
- Analysis: O(n)
- Scoring: O(n)
- **Total: O(n)** - Linear time complexity

### Memory Usage
- Typical lap (500 data points): ~100 KB
- All visualizations: Rendered on-demand in Plotly
- No file caching required

### Typical Execution Time
- Data loading: <100ms
- All processing: <200ms
- Visualization rendering: <500ms
- **Total: <1 second** for typical lap data

## Configuration Parameters

All thresholds can be adjusted in `app.py`:

```python
# Detection Thresholds
BRAKING_THRESHOLD = 0.2           # Proportional (0-1)
THROTTLE_THRESHOLD = 0.2          # Proportional (0-1)
STEERING_THRESHOLD = 5            # Degrees
SLIP_ANGLE_THRESHOLD = 5          # Degrees
YAW_THRESHOLD = 1                 # rad/s

# Oversteer/Understeer Detection
oversteer: yaw > 2 rad/s, slip > 8°
understeer: steering > 10°, yaw < 1 rad/s

# Harsh Braking
brake > 0.7 AND pitch > 2°

# Wheel Spin
throttle > 0.7 AND slip > 10°

# Instability
stability_index > 3.0

# RPM Efficiency (Ideal Range)
optimal_rpm: 4000-7000
```

### Adjusting for Different Vehicles

**Formula 1 / Single-Seater:**
- Lower thresholds (more aggressive driving expected)
- Higher efficiency RPM range (up to 15000)

**GT3 / Sports Car:**
- Moderate thresholds (current defaults)
- RPM range: 4000-7000

**Road Car:**
- Higher thresholds (less aggressive expected)
- Lower efficiency scores

## Error Handling

### Missing Data
```python
if critical_column is NaN:
    - Forward fill with last valid value
    - If no previous value, backward fill
    - If still NaN, skip that data point
```

### Invalid Values
```python
if value < minimum or value > maximum:
    - Clip to valid range
    - Log warning (optional)
    - Continue processing
```

### Missing GPS
```python
if latitude or longitude is missing:
    - Skip track map visualization
    - Continue with other visualizations
    - No error thrown
```

## Data Quality Recommendations

### Sampling Rate
- **Minimum:** 10 Hz (0.1 second intervals)
- **Recommended:** 50+ Hz (0.02 second intervals)
- **Professional:** 100+ Hz (0.01 second intervals)

### Data Duration
- **Minimum:** 10 seconds (single corner)
- **Typical:** 60-120 seconds (full lap)
- **Best:** 300+ seconds (multiple laps)

### Column Requirements
- **Essential (must have):** time, speed, throttle_input, brake_input
- **Recommended:** steering_angle, combined_slip_angle, yaw_moment, pitch, rpm, gear
- **Optional:** latitude, longitude

---

**Version:** 1.0
**Last Updated:** 2026-04-08
**Author:** Telemetry Analysis Team
