"""
ML Module Setup and Testing
Verify all dependencies and run quick validation tests
"""

import sys
import subprocess
import importlib


def check_ml_dependencies() -> bool:
    """
    Check if all required ML packages are installed
    
    Returns:
        True if all dependencies present, False otherwise
    """
    required_packages = {
        'sklearn': 'scikit-learn>=1.3',
        'pandas': 'pandas>=2.1',
        'numpy': 'numpy>=1.26'
    }
    
    missing = []
    
    for package_name, version_spec in required_packages.items():
        try:
            mod = importlib.import_module(package_name)
            print(f"✅ {package_name} installed")
        except ImportError:
            print(f"❌ {package_name} NOT installed")
            missing.append(version_spec)
    
    if missing:
        print(f"\n⚠️  Missing packages. Install with:")
        for pkg in missing:
            print(f"   pip install {pkg}")
        return False
    
    return True


def install_ml_dependencies():
    """Install required ML packages"""
    packages = [
        'scikit-learn>=1.3',
        'pandas>=2.1',
        'numpy>=1.26'
    ]
    
    print("Installing ML dependencies...")
    for package in packages:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '-q'])
    print("✅ All dependencies installed")


def test_ml_module():
    """Run quick validation test of ML module"""
    import pandas as pd
    import numpy as np
    
    from ml_module import (
        engineer_advanced_features,
        detect_anomalies,
        cluster_driving_styles,
        run_ml_pipeline
    )
    
    print("\n🧪 Testing ML Module...\n")
    
    # Create sample dataset
    n_samples = 100
    df_test = pd.DataFrame({
        'time': np.arange(n_samples) * 0.02,
        'speed': np.random.uniform(20, 80, n_samples),
        'throttle_input': np.random.uniform(0, 1, n_samples),
        'brake_input': np.random.uniform(0, 1, n_samples),
        'steering_angle': np.sin(np.arange(n_samples) * 0.1) * 3,
        'combined_slip_angle': np.random.uniform(-2, 2, n_samples),
        'yaw_moment': np.random.uniform(-100, 100, n_samples),
        'pitch': np.random.uniform(-5, 5, n_samples),
        'roll': np.random.uniform(-5, 5, n_samples),
        'rpm': np.random.uniform(3000, 7000, n_samples),
        'gear': np.random.choice([1, 2, 3, 4, 5], n_samples),
        'wheel_speed_fl': np.random.uniform(15, 85, n_samples),
        'wheel_speed_fr': np.random.uniform(15, 85, n_samples),
        'wheel_speed_rl': np.random.uniform(15, 85, n_samples),
        'wheel_speed_rr': np.random.uniform(15, 85, n_samples),
    })
    
    try:
        # Test 1: Feature Engineering
        print("1️⃣  Testing feature engineering...")
        df_eng = engineer_advanced_features(df_test)
        assert 'acceleration' in df_eng.columns, "Acceleration feature missing"
        assert 'slip_severity' in df_eng.columns, "Slip severity feature missing"
        assert 'stability_index' in df_eng.columns, "Stability index feature missing"
        print("   ✅ Feature engineering working\n")
        
        # Test 2: Anomaly Detection
        print("2️⃣  Testing anomaly detection...")
        anomalies = detect_anomalies(df_eng)
        assert len(anomalies) == len(df_eng), "Anomaly detection length mismatch"
        assert set(anomalies.unique()).issubset({-1, 1}), "Invalid anomaly values"
        print(f"   ✅ Anomaly detection found {(anomalies == -1).sum()} anomalies\n")
        
        # Test 3: Clustering
        print("3️⃣  Testing clustering...")
        clusters, kmeans = cluster_driving_styles(df_eng)
        assert len(clusters) == len(df_eng), "Clustering length mismatch"
        print(f"   ✅ Clustering identified {len(clusters.unique())} driving styles\n")
        
        # Test 4: Full Pipeline
        print("4️⃣  Testing full ML pipeline...")
        results = run_ml_pipeline(df_test)
        assert 'ml_score' in results['ml_scores'], "ML score not computed"
        assert results['ml_scores']['ml_score'] > 0, "ML score invalid"
        assert len(results['ml_insights']) > 0, "No insights generated"
        print(f"   ✅ Full pipeline working (ML Score: {results['ml_scores']['ml_score']:.1f})\n")
        
        print("✅ All ML module tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


def print_usage_guide():
    """Print quick start guide"""
    guide = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ML MODULE QUICK START GUIDE                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

📦 INSTALLATION
  pip install scikit-learn>=1.3 pandas>=2.1 numpy>=1.26

📚 FILES CREATED
  • ml_module.py        - Core ML functions
  • ml_integration.py   - Integration utilities
  • ml_examples.py      - Usage examples
  • ml_test.py          - Testing & setup

🚀 QUICK START
  
  # 1. Add to your app.py imports:
  from ml_module import run_ml_pipeline
  from ml_examples import example_enhanced_analysis_bundle_creation
  
  # 2. After loading telemetry, run ML pipeline:
  bundle = example_enhanced_analysis_bundle_creation(df)
  
  # 3. Access results:
  ml_score = bundle['ml_scores']['ml_score']
  anomalies = bundle['anomalies']
  insights = bundle['ml_insights']
  
  # 4. Display in Streamlit:
  st.metric("ML Score", f"{ml_score:.0f}/100")
  for insight in insights:
      st.write(f"• {insight['description']}")

🎯 KEY FEATURES

  ✓ Advanced Feature Engineering (13+ features)
    - acceleration, jerk, slip severity, stability index
    - wheel slip ratio, lateral G-force, RPM efficiency
  
  ✓ Anomaly Detection (Isolation Forest)
    - Detects unusual vehicle dynamics
    - Highlights sections needing attention
  
  ✓ Driving Style Classification (KMeans)
    - Smooth & Precise, Aggressive, Inconsistent
    - Automatic optimal cluster detection
  
  ✓ Driving Quality Prediction (Random Forest)
    - Classifies sections as good/bad quality
    - Provides confidence scores
  
  ✓ ML-Based Scoring
    - Composite score: 0-100
    - Components: stability, smoothness, control
    - Better than rule-based thresholds
  
  ✓ Intelligent Insights
    - Combines anomalies + clustering + quality
    - Actionable recommendations
    - Critical sections identification

📊 OUTPUT

  ml_results = run_ml_pipeline(df)
  
  ml_results['ml_scores'] = {
      'ml_score': 0-100,
      'stability_score': 0-100,
      'smoothness_score': 0-100,
      'control_score': 0-100,
      'normal_ratio': % of non-anomalous samples
  }
  
  ml_results['ml_insights'] = [
      {
          'type': 'ANOMALY|INSTABILITY|STYLE|QUALITY_DIP',
          'location': '~45m',
          'severity': 0-100,
          'description': '...',
          'recommendation': '...'
      }
  ]
  
  ml_results['clusters'] = Series of cluster IDs
  ml_results['anomalies'] = Series of -1 (anomaly) or 1 (normal)
  ml_results['quality_predictions'] = Series of 0 (bad) or 1 (good)

🔧 INTEGRATION OPTIONS

  Option A: Minimal (1 line)
    scores['ml_score'] = run_ml_pipeline(df)['ml_scores']['ml_score']
  
  Option B: Moderate (Use ML insights)
    bundle = example_enhanced_analysis_bundle_creation(df)
    # Display bundle['ml_insights']
  
  Option C: Full (All features)
    # Use example_generate_driver_report()
    # Use example_ml_suspension_recommendations()
    # Use example_show_improvement_roadmap()

🎓 ADVANCED USAGE

  # Get turn-level ML analysis
  from ml_integration import analyze_turn_with_ml
  turn_analysis = analyze_turn_with_ml(df, turn_data, model, kmeans)
  
  # Generate driver profile
  from ml_integration import generate_driver_profile
  profile = generate_driver_profile(df, ml_results)
  
  # Get critical sections
  from ml_integration import identify_critical_sections
  critical = identify_critical_sections(df, ml_results)
  
  # Get improvement roadmap
  from ml_integration import generate_improvement_roadmap
  roadmap = generate_improvement_roadmap(df, ml_results)

⚠️  IMPORTANT NOTES

  • ML pipeline adds 2-5 seconds to analysis time
  • Requires minimum 30 samples for meaningful results
  • Anomaly detection tuned to 5% contamination by default
  • All features normalized before model training
  • Random Forest uses 100 estimators, 10 max depth

❓ TROUBLESHOOTING

  ImportError: No module named 'sklearn'?
    → Run: python -m pip install scikit-learn
  
  "Not enough features" warning?
    → Dataset too small or missing columns
    → Add more telemetry data or check data format
  
  ML score always 50?
    → Dataset too uniform or not enough anomalies
    → This is normal for perfect driving!

═══════════════════════════════════════════════════════════════════════════════
    """
    print(guide)


if __name__ == "__main__":
    print("ML Module Setup")
    print("=" * 80)
    
    # Check dependencies
    if not check_ml_dependencies():
        response = input("\nInstall missing packages? (y/n): ")
        if response.lower() == 'y':
            install_ml_dependencies()
        else:
            print("Cannot proceed without dependencies.")
            sys.exit(1)
    
    # Run tests
    print("\n" + "=" * 80)
    if test_ml_module():
        print("\n" + "=" * 80)
        print_usage_guide()
    else:
        print("\n⚠️  Tests failed - check your installation")
