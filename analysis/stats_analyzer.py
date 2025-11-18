#!/usr/bin/env python3
"""
Statistical analysis of experimental results
Calculate confidence intervals, significance tests, etc.
"""

import json
import os
import argparse
import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Dict, Tuple


class StatsAnalyzer:
    """Statistical analysis of experimental results"""
    
    def __init__(self, results_dir='../results'):
        self.results_dir = results_dir
    
    def load_results(self, filename: str) -> dict:
        """Load results from JSON file"""
        filepath = os.path.join(self.results_dir, filename)
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def calculate_confidence_interval(self, data: List[float], 
                                     confidence: float = 0.95) -> Tuple[float, float, float]:
        """
        Calculate mean and confidence interval
        
        Args:
            data: List of measurements
            confidence: Confidence level (default 0.95 for 95%)
        
        Returns:
            Tuple of (mean, lower_bound, upper_bound)
        """
        n = len(data)
        mean = np.mean(data)
        std_err = stats.sem(data)
        margin = std_err * stats.t.ppf((1 + confidence) / 2, n - 1)
        
        return mean, mean - margin, mean + margin
    
    def t_test_comparison(self, data1: List[float], data2: List[float]) -> Dict:
        """
        Perform two-sample t-test
        
        Args:
            data1: First dataset
            data2: Second dataset
        
        Returns:
            Dictionary with test results
        """
        t_stat, p_value = stats.ttest_ind(data1, data2)
        
        # Calculate effect size (Cohen's d)
        pooled_std = np.sqrt((np.std(data1)**2 + np.std(data2)**2) / 2)
        cohens_d = (np.mean(data1) - np.mean(data2)) / pooled_std
        
        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'cohens_d': cohens_d,
            'effect_size': self._interpret_effect_size(cohens_d)
        }
    
    def _interpret_effect_size(self, d: float) -> str:
        """Interpret Cohen's d effect size"""
        d_abs = abs(d)
        if d_abs < 0.2:
            return 'negligible'
        elif d_abs < 0.5:
            return 'small'
        elif d_abs < 0.8:
            return 'medium'
        else:
            return 'large'
    
    def analyze_incast_comparison(self, ecmp_file: str, hula_file: str):
        """
        Comprehensive analysis of ECMP vs HULA incast results
        
        Args:
            ecmp_file: ECMP results file
            hula_file: HULA results file
        """
        print("\n" + "="*70)
        print("INCAST SCENARIO: STATISTICAL ANALYSIS")
        print("="*70 + "\n")
        
        # Load data
        ecmp_data = self.load_results(ecmp_file)
        hula_data = self.load_results(hula_file)
        
        # Extract metrics
        ecmp_throughput = [f['bits_per_second'] / (1024**2) 
                          for f in ecmp_data['flows'] if 'bits_per_second' in f]
        hula_throughput = [f['bits_per_second'] / (1024**2) 
                          for f in hula_data['flows'] if 'bits_per_second' in f]
        
        ecmp_retrans = [f.get('retransmits', 0) for f in ecmp_data['flows']]
        hula_retrans = [f.get('retransmits', 0) for f in hula_data['flows']]
        
        # Throughput analysis
        print("THROUGHPUT ANALYSIS:")
        print("-" * 70)
        
        ecmp_mean, ecmp_ci_low, ecmp_ci_high = self.calculate_confidence_interval(ecmp_throughput)
        hula_mean, hula_ci_low, hula_ci_high = self.calculate_confidence_interval(hula_throughput)
        
        print(f"ECMP:")
        print(f"  Mean: {ecmp_mean:.2f} Mbps")
        print(f"  95% CI: [{ecmp_ci_low:.2f}, {ecmp_ci_high:.2f}]")
        print(f"  Std Dev: {np.std(ecmp_throughput):.2f}")
        print(f"  Min/Max: {np.min(ecmp_throughput):.2f} / {np.max(ecmp_throughput):.2f}")
        
        print(f"\nHULA:")
        print(f"  Mean: {hula_mean:.2f} Mbps")
        print(f"  95% CI: [{hula_ci_low:.2f}, {hula_ci_high:.2f}]")
        print(f"  Std Dev: {np.std(hula_throughput):.2f}")
        print(f"  Min/Max: {np.min(hula_throughput):.2f} / {np.max(hula_throughput):.2f}")
        
        # Statistical test
        t_test = self.t_test_comparison(ecmp_throughput, hula_throughput)
        
        print(f"\nStatistical Significance Test:")
        print(f"  t-statistic: {t_test['t_statistic']:.4f}")
        print(f"  p-value: {t_test['p_value']:.6f}")
        print(f"  Significant (α=0.05): {'YES' if t_test['significant'] else 'NO'}")
        print(f"  Effect size (Cohen's d): {t_test['cohens_d']:.4f} ({t_test['effect_size']})")
        
        improvement = ((hula_mean - ecmp_mean) / ecmp_mean) * 100
        print(f"\nThroughput Improvement: {improvement:+.2f}%")
        
        # Retransmit analysis
        print("\n" + "-" * 70)
        print("RETRANSMIT ANALYSIS:")
        print("-" * 70)
        
        print(f"ECMP Total Retransmits: {sum(ecmp_retrans)}")
        print(f"HULA Total Retransmits: {sum(hula_retrans)}")
        
        retrans_reduction = ((sum(ecmp_retrans) - sum(hula_retrans)) / max(sum(ecmp_retrans), 1)) * 100
        print(f"Retransmit Reduction: {retrans_reduction:.2f}%")
        
        # Fairness analysis (Jain's Fairness Index)
        print("\n" + "-" * 70)
        print("FAIRNESS ANALYSIS:")
        print("-" * 70)
        
        ecmp_jfi = self.jains_fairness_index(ecmp_throughput)
        hula_jfi = self.jains_fairness_index(hula_throughput)
        
        print(f"Jain's Fairness Index (0-1, higher is better):")
        print(f"  ECMP: {ecmp_jfi:.4f}")
        print(f"  HULA: {hula_jfi:.4f}")
        print(f"  Improvement: {((hula_jfi - ecmp_jfi) / ecmp_jfi * 100):+.2f}%")
        
        print("\n" + "="*70 + "\n")
    
    def jains_fairness_index(self, data: List[float]) -> float:
        """
        Calculate Jain's Fairness Index
        
        Args:
            data: List of measurements (e.g., throughputs)
        
        Returns:
            Fairness index (0 to 1)
        """
        n = len(data)
        if n == 0:
            return 0.0
        
        sum_x = sum(data)
        sum_x_sq = sum(x**2 for x in data)
        
        return (sum_x ** 2) / (n * sum_x_sq)
    
    def generate_summary_report(self, output_file: str = '../results/summary_report.txt'):
        """Generate comprehensive summary report"""
        
        # Find all result files
        result_files = [f for f in os.listdir(self.results_dir) 
                       if f.endswith('.json')]
        
        with open(output_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("EXPERIMENTAL RESULTS SUMMARY REPORT\n")
            f.write("="*70 + "\n\n")
            
            for result_file in result_files:
                f.write(f"File: {result_file}\n")
                f.write("-" * 70 + "\n")
                
                try:
                    data = self.load_results(result_file)
                    f.write(f"Test Type: {data.get('test_type', 'unknown')}\n")
                    f.write(f"Timestamp: {data.get('timestamp', 'unknown')}\n")
                    
                    if 'metrics' in data:
                        f.write("\nMetrics:\n")
                        for key, value in data['metrics'].items():
                            f.write(f"  {key}: {value}\n")
                    
                    f.write("\n")
                    
                except Exception as e:
                    f.write(f"Error processing file: {e}\n\n")
        
        print(f"✓ Summary report saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Statistical Analysis')
    parser.add_argument('--results-dir', default='../results',
                       help='Results directory')
    parser.add_argument('--incast-ecmp', help='ECMP incast results file')
    parser.add_argument('--incast-hula', help='HULA incast results file')
    parser.add_argument('--summary', action='store_true',
                       help='Generate summary report')
    
    args = parser.parse_args()
    
    analyzer = StatsAnalyzer(args.results_dir)
    
    if args.incast_ecmp and args.incast_hula:
        analyzer.analyze_incast_comparison(args.incast_ecmp, args.incast_hula)
    
    if args.summary:
        analyzer.generate_summary_report()


if __name__ == '__main__':
    main()
