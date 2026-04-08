# New insights generation for handling dynamics focus

def generate_insights_handling(
    data,
    events,
    event_counts,
    scores,
    thresholds,
    EVENT_STYLES,
    dominant_location_label,
    mask_ratio,
) -> list:
    """Generate handling-focused insights with driver technique and suspension recommendations."""
    ranked_insights = []

    def add(priority, text):
        ranked_insights.append((priority, text))

    # OVERSTEER ANALYSIS
    if event_counts["oversteer"] > 0:
        turn_id, distance = dominant_location_label(data, events["oversteer"])
        peak_slip = float(data.loc[events["oversteer"], "slip_severity"].max())
        location_str = f"Turn {turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(100, f"[OVERSTEER] {location_str}: Rear slides with peak {peak_slip:.1f}° slip. "
                f"Driver→ reduce entry speed 2-3 km/h, delay throttle application. "
                f"Setup→ increase rear ARB +20%, soften front ARB 10%, increase front damping +15%.")

    # UNDERSTEER ANALYSIS
    if event_counts["understeer"] > 0:
        turn_id, distance = dominant_location_label(data, events["understeer"])
        location_str = f"Turn {turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(95, f"[UNDERSTEER] {location_str}: Front insufficient grip. "
                f"Driver→ brake release earlier, use progressive steering inputs. "
                f"Setup→ reduce front ARB -20%, increase front camber -0.4°, lower front 5mm.")

    # HARSH BRAKING ANALYSIS
    if event_counts["harsh_braking"] > 0:
        turn_id, distance = dominant_location_label(data, events["harsh_braking"])
        peak_pitch = float(data.loc[events["harsh_braking"], "pitch_abs"].max())
        location_str = f"Turn {turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(92, f"[HARSH BRAKING] {location_str}: Platform upset (pitch {peak_pitch:.2f}°). "
                f"Driver→ build pedal pressure gradually over 0.5-1.0s, modulate mid-corner. "
                f"Setup→ soften front springs -8%, reduce front ride height 5mm, adjust brake bias forward 1%.")

    # LATE BRAKING
    if event_counts["late_braking"] > 0:
        turn_id, distance = dominant_location_label(data, events["late_braking"])
        location_str = f"Turn {turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(88, f"[LATE BRAKING] {location_str}: Entry speed remains high into corner. "
                f"Driver→ begin braking 0.5-1.0s earlier, spread deceleration phase longer. "
                f"Setup→ increase brake reactivity via bias adjustment forward.")

    # EARLY BRAKING
    elif event_counts["early_braking"] > 0:
        turn_id, distance = dominant_location_label(data, events["early_braking"])
        location_str = f"Turn {turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(82, f"[EARLY BRAKING] {location_str}: Scrubbing speed unnecessarily early. "
                f"Driver→ brake 0.3-0.5s later, use stronger pedal intensity for shorter duration. "
                f"Setup→ fine-tune brake bias balance for confidence.")

    # WHEEL SPIN ANALYSIS
    if event_counts["wheel_spin"] > 0:
        turn_id, distance = dominant_location_label(data, events["wheel_spin"])
        location_str = f"Turn {turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(84, f"[TRACTION LOSS] {location_str}: Wheelspin on exit under acceleration. "
                f"Driver→ wait until steering <5° before full throttle, squeeze input progressively. "
                f"Setup→ increase rear spring rate +10%, rear ARB +20%, reduce rear rebound damping -10%.")

    # INSTABILITY
    unstable_ratio = mask_ratio(events["unstable"]) * 100
    if unstable_ratio > 8:
        turn_id, distance = dominant_location_label(data, events["unstable"])
        location_str = f"Turn {turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(70, f"[PLATFORM INSTABILITY] {location_str}: Vehicle unstable for {unstable_ratio:.1f}% of lap. "
                f"Driver→ smooth all pedal transitions, single steering input per corner. "
                f"Setup→ increase overall damping +10-15%, re-balance front/rear springs.")

    # RPM EFFICIENCY (secondary, fuel-related)
    if event_counts["high_rpm_issue"] > 0:
        add(65, f"[RPM EFFICIENCY] Frequent overshifting on straights (>{thresholds['rpm_high']:.0f} RPM). "
                f"Driver→ shift 500 RPM earlier for better mid-range responsiveness. "
                f"Secondary note: Lower average RPM may improve fuel economy on long runs.")

    if event_counts["low_rpm_issue"] > 0:
        add(63, f"[RPM EFFICIENCY] Engine drops below efficient band (>{thresholds['rpm_low']:.0f} RPM). "
                f"Driver→ downshift earlier or hold lower gear longer in acceleration zones. "
                f"Secondary note: Higher RPM zones use more fuel but provide stronger torque when needed.")

    # BRAKING SMOOTHNESS
    if scores.get("braking_score", 0) < 70:
        add(60, "[BRAKING PROGRESSION] Brake application lacks smoothness. "
                "Driver→ practice gradual pedal build-up and modulation through corners. "
                "Setup→ verify brake pads are fresh, check brake fluid condition.")

    # STEERING PRECISION
    if scores.get("handling_score", 0) < 70:
        add(58, "[STEERING PRECISION] Steering inputs are wide or abrupt. "
                "Driver→ reduce steering wheel movements, aim for single-input corners. "
                "Setup→ verify steering ratio and damper functionality.")

    if not ranked_insights:
        add(40, "[CLEAN LAP] Telemetry shows good fundamentals. Next improvements: "
                "1) Feed throttle slightly earlier on exits, 2) Reduce brake modulation mid-corner, "
                "3) Use shallower apexes to exit faster.")

    ranked_insights.sort(key=lambda x: x[0], reverse=True)
    unique_text = []
    seen = set()
    for _, text in ranked_insights:
        if text not in seen:
            seen.add(text)
            unique_text.append(text)
        if len(unique_text) >= 8:
            break
    
    return unique_text
