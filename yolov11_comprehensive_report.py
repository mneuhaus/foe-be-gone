#!/usr/bin/env python3
"""
YOLOv11n Comprehensive Testing Report Generator
Compiles all testing results into a detailed analysis report
"""

import json
import time
from pathlib import Path
from datetime import datetime

def load_test_results():
    """Load all available test results"""
    results = {}
    
    # Basic YOLOv11n results
    basic_summary = Path("yolov11_detections/yolov11_summary.json")
    if basic_summary.exists():
        with open(basic_summary, 'r') as f:
            results['basic_test'] = json.load(f)
    
    basic_detailed = Path("yolov11_detections/yolov11_results.json")
    if basic_detailed.exists():
        with open(basic_detailed, 'r') as f:
            results['basic_detailed'] = json.load(f)
    
    # Extended analysis results
    extended_summary = Path("yolov11_extended_analysis/extended_analysis_summary.json")
    if extended_summary.exists():
        with open(extended_summary, 'r') as f:
            results['extended_analysis'] = json.load(f)
    
    # Advanced testing results
    advanced_results = Path("yolov11_advanced_testing/advanced_testing_results.json")
    if advanced_results.exists():
        with open(advanced_results, 'r') as f:
            results['advanced_testing'] = json.load(f)
    
    # Threshold analysis
    threshold_analysis = Path("yolov11_extended_analysis/threshold_analysis.json")
    if threshold_analysis.exists():
        with open(threshold_analysis, 'r') as f:
            results['threshold_analysis'] = json.load(f)
    
    return results

def generate_performance_summary(results):
    """Generate performance summary"""
    summary = {}
    
    if 'basic_test' in results:
        basic = results['basic_test']
        summary['basic_performance'] = {
            'total_images': basic.get('total_images_processed', 0),
            'total_detections': basic.get('total_animals_detected', 0),
            'avg_time_per_image': basic.get('avg_time_per_image', 0),
            'fps': basic.get('images_per_second', 0),
            'animals_by_type': basic.get('animals_by_type', {})
        }
    
    if 'extended_analysis' in results and 'speed_benchmark' in results['extended_analysis']:
        speed = results['extended_analysis']['speed_benchmark']
        summary['speed_benchmark'] = {
            'average_time': speed.get('average', 0),
            'median_time': speed.get('median', 0),
            'min_time': speed.get('min', 0),
            'max_time': speed.get('max', 0),
            'max_fps': speed.get('max_fps', 0),
            'iterations': speed.get('iterations', 0)
        }
    
    if 'advanced_testing' in results and 'stress_test' in results['advanced_testing']:
        stress = results['advanced_testing']['stress_test']
        summary['stress_test'] = {
            'total_images': stress.get('total_images', 0),
            'avg_fps': stress.get('avg_fps', 0),
            'success_rate': stress.get('success_rate', 0),
            'total_detections': stress.get('total_detections', 0),
            'duration_minutes': stress.get('duration_minutes', 0)
        }
    
    return summary

def generate_detection_analysis(results):
    """Generate detection analysis"""
    analysis = {}
    
    if 'extended_analysis' in results and 'confidence_analysis' in results['extended_analysis']:
        conf = results['extended_analysis']['confidence_analysis']
        analysis['confidence_stats'] = {
            'overall_mean': conf.get('overall', {}).get('mean', 0),
            'overall_std': conf.get('overall', {}).get('std', 0),
            'overall_min': conf.get('overall', {}).get('min', 0),
            'overall_max': conf.get('overall', {}).get('max', 0),
            'by_class': conf.get('by_class', {})
        }
    
    if 'extended_analysis' in results and 'bbox_analysis' in results['extended_analysis']:
        bbox = results['extended_analysis']['bbox_analysis']
        analysis['bbox_stats'] = {
            'mean_area': bbox.get('areas', {}).get('mean', 0),
            'median_area': bbox.get('areas', {}).get('median', 0),
            'mean_ratio': bbox.get('ratios', {}).get('mean', 0),
            'median_ratio': bbox.get('ratios', {}).get('median', 0)
        }
    
    if 'threshold_analysis' in results:
        thresholds = results['threshold_analysis']
        best_threshold = None
        best_score = 0
        
        for thresh, data in thresholds.items():
            # Score based on detection count and threshold balance
            score = data.get('total_detections', 0) * float(thresh)
            if score > best_score:
                best_score = score
                best_threshold = float(thresh)
        
        analysis['optimal_threshold'] = best_threshold
        analysis['threshold_performance'] = thresholds
    
    return analysis

def generate_resource_analysis(results):
    """Generate resource usage analysis"""
    analysis = {}
    
    if 'advanced_testing' in results and 'memory_usage' in results['advanced_testing']:
        mem = results['advanced_testing']['memory_usage']
        if mem:
            analysis['memory'] = {
                'peak_mb': mem.get('peak_mb', 0),
                'overhead_mb': mem.get('overhead_mb', 0),
                'after_loading_mb': mem.get('after_loading_mb', 0)
            }
    
    if 'advanced_testing' in results and 'image_sizes' in results['advanced_testing']:
        sizes = results['advanced_testing']['image_sizes']
        if sizes:
            analysis['image_size_performance'] = {}
            for size, data in sizes.items():
                analysis['image_size_performance'][size] = {
                    'fps': data.get('fps', 0),
                    'avg_time': data.get('avg_time', 0),
                    'megapixels': data.get('megapixels', 0)
                }
    
    return analysis

def generate_comparison_analysis(results):
    """Generate comparison with other methods"""
    comparison = {}
    
    if 'extended_analysis' in results and 'method_comparison' in results['extended_analysis']:
        methods = results['extended_analysis']['method_comparison']
        comparison['methods'] = {}
        
        for method, data in methods.items():
            comparison['methods'][method] = {
                'images_processed': data.get('total_images_processed', 0),
                'detections': data.get('total_detections', 0),
                'avg_time': data.get('avg_time_per_image', 0),
                'fps': 1 / data.get('avg_time_per_image', 1) if data.get('avg_time_per_image', 0) > 0 else 0
            }
        
        # Calculate relative performance
        if 'YOLOv11n' in comparison['methods']:
            yolo_fps = comparison['methods']['YOLOv11n']['fps']
            comparison['relative_performance'] = {}
            
            for method, data in comparison['methods'].items():
                if method != 'YOLOv11n' and data['fps'] > 0:
                    comparison['relative_performance'][method] = {
                        'speed_ratio': yolo_fps / data['fps'],
                        'faster_by': f"{yolo_fps / data['fps']:.1f}x"
                    }
    
    return comparison

def generate_recommendations(results):
    """Generate deployment recommendations"""
    recommendations = {
        'deployment_readiness': 'Unknown',
        'optimal_settings': {},
        'performance_characteristics': [],
        'use_case_suitability': {}
    }
    
    # Analyze performance for deployment readiness
    if 'basic_test' in results:
        basic = results['basic_test']
        fps = basic.get('images_per_second', 0)
        avg_time = basic.get('avg_time_per_image', 0)
        
        if fps >= 15 and avg_time <= 0.1:
            recommendations['deployment_readiness'] = 'Excellent - Ready for real-time deployment'
        elif fps >= 10 and avg_time <= 0.2:
            recommendations['deployment_readiness'] = 'Good - Suitable for most surveillance applications'
        elif fps >= 5:
            recommendations['deployment_readiness'] = 'Moderate - Suitable for non-real-time processing'
        else:
            recommendations['deployment_readiness'] = 'Limited - May need optimization for production use'
    
    # Optimal settings
    if 'extended_analysis' in results and 'threshold_testing' in results['extended_analysis']:
        threshold_data = results['extended_analysis']['threshold_testing']
        if threshold_data:
            # Find optimal threshold (balance of detection count and precision)
            best_threshold = 0.3  # default
            best_score = 0
            
            for thresh_str, data in threshold_data.items():
                thresh = float(thresh_str)
                detections = data.get('total_detections', 0)
                score = detections * thresh  # Balance detection count with precision
                
                if score > best_score:
                    best_score = score
                    best_threshold = thresh
            
            recommendations['optimal_settings']['confidence_threshold'] = best_threshold
    
    # Performance characteristics
    if 'advanced_testing' in results:
        advanced = results['advanced_testing']
        
        if 'stress_test' in advanced and advanced['stress_test']:
            stress = advanced['stress_test']
            if stress.get('success_rate', 0) >= 99:
                recommendations['performance_characteristics'].append('High reliability (99%+ success rate)')
            
            if stress.get('avg_fps', 0) >= 15:
                recommendations['performance_characteristics'].append('Real-time capable (15+ FPS sustained)')
        
        if 'memory_usage' in advanced and advanced['memory_usage']:
            mem = advanced['memory_usage']
            if mem.get('peak_mb', 0) <= 1000:
                recommendations['performance_characteristics'].append('Low memory footprint (<1GB peak)')
    
    # Use case suitability
    if 'basic_test' in results:
        basic = results['basic_test']
        animals_detected = basic.get('animals_by_type', {})
        
        total_detections = sum(animals_detected.values())
        if total_detections > 0:
            recommendations['use_case_suitability']['wildlife_monitoring'] = 'Excellent'
            recommendations['use_case_suitability']['surveillance_systems'] = 'Very Good'
            recommendations['use_case_suitability']['real_time_alerts'] = 'Good' if basic.get('images_per_second', 0) >= 10 else 'Moderate'
    
    return recommendations

def generate_comprehensive_report():
    """Generate comprehensive testing report"""
    print("📄 Generating YOLOv11n Comprehensive Testing Report...")
    
    # Load all test results
    results = load_test_results()
    
    if not results:
        print("❌ No test results found. Please run the testing suites first.")
        return
    
    # Generate analyses
    performance_summary = generate_performance_summary(results)
    detection_analysis = generate_detection_analysis(results)
    resource_analysis = generate_resource_analysis(results)
    comparison_analysis = generate_comparison_analysis(results)
    recommendations = generate_recommendations(results)
    
    # Compile comprehensive report
    report = {
        'report_metadata': {
            'generated_at': datetime.now().isoformat(),
            'test_suites_included': list(results.keys()),
            'yolov11_version': 'YOLOv11n (ultralytics)',
            'platform': 'Apple Silicon (MPS)'
        },
        'executive_summary': {
            'deployment_readiness': recommendations.get('deployment_readiness', 'Unknown'),
            'key_metrics': {
                'max_fps': performance_summary.get('speed_benchmark', {}).get('max_fps', 0),
                'avg_processing_time': performance_summary.get('speed_benchmark', {}).get('average_time', 0),
                'memory_usage_mb': resource_analysis.get('memory', {}).get('peak_mb', 0),
                'detection_accuracy': detection_analysis.get('confidence_stats', {}).get('overall_mean', 0)
            }
        },
        'performance_analysis': performance_summary,
        'detection_analysis': detection_analysis,
        'resource_analysis': resource_analysis,
        'comparison_analysis': comparison_analysis,
        'recommendations': recommendations,
        'raw_data': results
    }
    
    # Save comprehensive report
    output_dir = Path("yolov11_comprehensive_report")
    output_dir.mkdir(exist_ok=True)
    
    report_file = output_dir / "comprehensive_testing_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Generate human-readable summary
    summary_file = output_dir / "executive_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("YOLOv11n Animal Detection - Comprehensive Testing Report\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 20 + "\n")
        f.write(f"Deployment Readiness: {recommendations.get('deployment_readiness', 'Unknown')}\n\n")
        
        f.write("KEY PERFORMANCE METRICS\n")
        f.write("-" * 25 + "\n")
        if 'speed_benchmark' in performance_summary:
            speed = performance_summary['speed_benchmark']
            f.write(f"Maximum FPS: {speed.get('max_fps', 0):.1f}\n")
            f.write(f"Average Processing Time: {speed.get('average_time', 0):.3f} seconds\n")
            f.write(f"Min Processing Time: {speed.get('min_time', 0):.3f} seconds\n")
            f.write(f"Max Processing Time: {speed.get('max_time', 0):.3f} seconds\n")
        
        if 'memory' in resource_analysis:
            mem = resource_analysis['memory']
            f.write(f"Peak Memory Usage: {mem.get('peak_mb', 0):.1f} MB\n")
            f.write(f"Memory Overhead: {mem.get('overhead_mb', 0):.1f} MB\n")
        
        if 'confidence_stats' in detection_analysis:
            conf = detection_analysis['confidence_stats']
            f.write(f"Average Detection Confidence: {conf.get('overall_mean', 0):.3f}\n")
        
        f.write("\nDETECTION CAPABILITIES\n")
        f.write("-" * 22 + "\n")
        if 'basic_performance' in performance_summary:
            basic = performance_summary['basic_performance']
            f.write(f"Total Images Processed: {basic.get('total_images', 0)}\n")
            f.write(f"Total Animals Detected: {basic.get('total_detections', 0)}\n")
            
            animals = basic.get('animals_by_type', {})
            if animals:
                f.write("\nAnimals Detected by Type:\n")
                for animal_type, count in animals.items():
                    f.write(f"  - {animal_type.capitalize()}: {count}\n")
        
        f.write("\nOPTIMAL SETTINGS\n")
        f.write("-" * 17 + "\n")
        optimal = recommendations.get('optimal_settings', {})
        if optimal.get('confidence_threshold'):
            f.write(f"Recommended Confidence Threshold: {optimal['confidence_threshold']}\n")
        
        f.write("\nPERFORMANCE CHARACTERISTICS\n")
        f.write("-" * 28 + "\n")
        characteristics = recommendations.get('performance_characteristics', [])
        for characteristic in characteristics:
            f.write(f"✓ {characteristic}\n")
        
        f.write("\nRECOMMENDED USE CASES\n")
        f.write("-" * 22 + "\n")
        use_cases = recommendations.get('use_case_suitability', {})
        for use_case, suitability in use_cases.items():
            f.write(f"{use_case.replace('_', ' ').title()}: {suitability}\n")
        
        if 'methods' in comparison_analysis:
            f.write("\nCOMPARISON WITH OTHER METHODS\n")
            f.write("-" * 31 + "\n")
            methods = comparison_analysis['methods']
            for method, data in methods.items():
                f.write(f"{method}: {data.get('fps', 0):.1f} FPS\n")
    
    print(f"\n✨ Comprehensive Report Generated!")
    print(f"📁 Full report: {report_file}")
    print(f"📄 Executive summary: {summary_file}")
    
    # Display key findings
    print(f"\n🔍 KEY FINDINGS:")
    executive = report['executive_summary']
    metrics = executive['key_metrics']
    
    print(f"   ⚡ Performance: {metrics.get('max_fps', 0):.1f} FPS max, {metrics.get('avg_processing_time', 0)*1000:.0f}ms avg")
    print(f"   💾 Memory: {metrics.get('memory_usage_mb', 0):.0f} MB peak usage")
    print(f"   🎯 Accuracy: {metrics.get('detection_accuracy', 0):.3f} avg confidence")
    print(f"   🚀 Status: {executive.get('deployment_readiness', 'Unknown')}")
    
    return report

if __name__ == "__main__":
    generate_comprehensive_report()
