#!/usr/bin/env python3
"""
Microburst traffic scenario - Sudden traffic spikes
Tests ability to handle bursty traffic patterns
"""

import sys
import time
import argparse
import json
import subprocess
from datetime import datetime
from traffic_gen import TrafficGenerator


class MicroburstTest:
    """Microburst traffic test scenario"""
    
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)
        self.traffic_gen = TrafficGenerator()
        self.results = {
            'test_type': 'microburst',
            'timestamp': datetime.now().isoformat(),
            'bursts': []
        }
    
    def load_config(self, config_file: str) -> dict:
        """Load test configuration"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def generate_burst(self, senders: list, receiver: str, 
                      burst_size_mb: int, burst_rate: str = '1G'):
        """
        Generate a single microburst
        
        Args:
            senders: List of sender hosts
            receiver: Receiver host
            burst_size_mb: Size of burst in MB
            burst_rate: Burst sending rate
        
        Returns:
            Dictionary with burst results
        """
        print(f"\n→ Generating {burst_size_mb}MB burst from {len(senders)} senders")
        
        burst_start = time.time()
        burst_results = []
        
        # Calculate duration to send burst_size_mb at burst_rate
        # For simplicity, use fixed short duration
        duration = max(1, int(burst_size_mb / 100))  # Rough estimate
        
        for sender in senders:
            result = self.traffic_gen.run_iperf_client(
                sender, receiver, 
                duration=duration,
                bandwidth=burst_rate
            )
            burst_results.append(result)
        
        burst_end = time.time()
        
        burst_summary = {
            'burst_id': len(self.results['bursts']) + 1,
            'start_time': burst_start,
            'end_time': burst_end,
            'duration': burst_end - burst_start,
            'num_senders': len(senders),
            'target_size_mb': burst_size_mb,
            'flows': burst_results
        }
        
        # Calculate actual bytes sent
        total_bytes = sum(f.get('bytes_transferred', 0) for f in burst_results)
        burst_summary['actual_size_mb'] = total_bytes / (1024**2)
        burst_summary['total_retransmits'] = sum(
            f.get('retransmits', 0) for f in burst_results
        )
        
        return burst_summary
    
    def run_test(self):
        """Execute microburst test"""
        microburst_config = self.config['scenarios']['microburst']
        
        burst_size_mb = microburst_config['burst_size_mb']
        inter_burst_ms = microburst_config['inter_burst_ms']
        num_bursts = microburst_config.get('num_bursts', 10)
        num_senders = microburst_config.get('num_senders', 5)
        
        print(f"\n{'='*60}")
        print(f"MICROBURST TEST")
        print(f"Burst size: {burst_size_mb}MB, Inter-burst: {inter_burst_ms}ms")
        print(f"Number of bursts: {num_bursts}, Senders per burst: {num_senders}")
        print(f"{'='*60}\n")
        
        # Generate sender and receiver IPs
        senders = [f"10.0.1.{i+1}" for i in range(num_senders)]
        receiver = "10.0.2.1"
        
        # Start receiver
        self.traffic_gen.start_iperf_server(receiver)
        time.sleep(2)
        
        # Generate bursts with inter-burst intervals
        for burst_num in range(num_bursts):
            print(f"\n[Burst {burst_num + 1}/{num_bursts}]")
            
            burst_result = self.generate_burst(
                senders, receiver, burst_size_mb
            )
            self.results['bursts'].append(burst_result)
            
            # Wait before next burst
            if burst_num < num_bursts - 1:
                wait_time = inter_burst_ms / 1000.0
                print(f"  Waiting {inter_burst_ms}ms before next burst...")
                time.sleep(wait_time)
        
        # Calculate overall metrics
        self.calculate_metrics()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"microburst_results_{timestamp}.json"
        self.save_results(results_file)
    
    def calculate_metrics(self):
        """Calculate aggregate metrics across all bursts"""
        bursts = self.results['bursts']
        
        if not bursts:
            print("No burst results to analyze")
            return
        
        total_bursts = len(bursts)
        total_mb_sent = sum(b['actual_size_mb'] for b in bursts)
        total_retransmits = sum(b['total_retransmits'] for b in bursts)
        avg_burst_duration = sum(b['duration'] for b in bursts) / total_bursts
        
        # Calculate per-burst statistics
        burst_sizes = [b['actual_size_mb'] for b in bursts]
        min_burst = min(burst_sizes)
        max_burst = max(burst_sizes)
        avg_burst = sum(burst_sizes) / len(burst_sizes)
        
        metrics = {
            'total_bursts': total_bursts,
            'total_mb_transferred': total_mb_sent,
            'total_retransmits': total_retransmits,
            'avg_burst_duration_sec': avg_burst_duration,
            'min_burst_size_mb': min_burst,
            'max_burst_size_mb': max_burst,
            'avg_burst_size_mb': avg_burst,
            'burst_size_variance': sum((x - avg_burst)**2 for x in burst_sizes) / len(burst_sizes)
        }
        
        self.results['metrics'] = metrics
        
        print("\n" + "="*60)
        print("TEST RESULTS:")
        print("="*60)
        print(f"Total bursts: {total_bursts}")
        print(f"Total data transferred: {total_mb_sent:.2f} MB")
        print(f"Average burst size: {avg_burst:.2f} MB")
        print(f"Burst size range: [{min_burst:.2f}, {max_burst:.2f}] MB")
        print(f"Average burst duration: {avg_burst_duration:.3f}s")
        print(f"Total retransmits: {total_retransmits}")
        print(f"Retransmit rate: {total_retransmits / max(total_mb_sent * 1024 / 1.5, 1):.4f}")
        print("="*60 + "\n")
    
    def save_results(self, filename: str):
        """Save test results"""
        filepath = f"../results/{filename}"
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✓ Results saved to {filepath}")


def main():
    parser = argparse.ArgumentParser(description='Microburst Test')
    parser.add_argument('--config', default='../configs/experiment_config.json',
                       help='Configuration file')
    
    args = parser.parse_args()
    
    test = MicroburstTest(args.config)
    test.run_test()


if __name__ == '__main__':
    main()
