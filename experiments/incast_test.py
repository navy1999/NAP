#!/usr/bin/env python3
"""
Incast traffic scenario - Many senders to one receiver
Tests congestion handling and tail latency
"""

import sys
import time
import argparse
import json
from datetime import datetime
from traffic_gen import TrafficGenerator


class IncastTest:
    """Incast traffic test scenario"""
    
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)
        self.traffic_gen = TrafficGenerator()
        self.results = {
            'test_type': 'incast',
            'timestamp': datetime.now().isoformat(),
            'flows': []
        }
    
    def load_config(self, config_file: str) -> dict:
        """Load test configuration"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def run_test(self):
        """Execute incast test"""
        incast_config = self.config['scenarios']['incast']
        
        num_senders = incast_config['num_senders']
        duration = incast_config['duration_sec']
        bandwidth = incast_config['bandwidth_per_flow']
        
        print("\n" + "=" * 60)
        print("INCAST TEST: {} senders \u2192 1 receiver".format(num_senders))
        print("Duration: {}s, Per-flow BW: {}".format(duration, bandwidth))
        print("=" * 60 + "\n")
        
        # Generate sender and receiver IPs
        senders = ["10.0.1.{}".format(i + 1) for i in range(num_senders)]
        receiver = "10.0.2.1"
        
        # Run incast pattern
        flow_results = self.traffic_gen.incast_pattern(
            senders, receiver, duration, bandwidth
        )
        
        self.results['flows'] = flow_results
        self.results['num_senders'] = num_senders
        self.results['receiver'] = receiver
        
        # Calculate metrics
        self.calculate_metrics()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = "incast_results_{}.json".format(timestamp)
        self.save_results(results_file)
    
    def calculate_metrics(self):
        """Calculate aggregate metrics"""
        flows = self.results['flows']
        
        if not flows:
            print("No flow results to analyze")
            return
        
        total_bytes = sum(f.get('bytes_transferred', 0) for f in flows)
        total_retransmits = sum(f.get('retransmits', 0) for f in flows)
        avg_throughput = sum(f.get('bits_per_second', 0) for f in flows) / float(len(flows))
        
        packet_loss_rate = 0.0
        denom = max(total_bytes / 1500.0, 1.0)
        packet_loss_rate = total_retransmits / denom
        
        num_successful = len([f for f in flows if 'error' not in f])
        
        metrics = {
            'total_bytes_transferred': total_bytes,
            'total_retransmits': total_retransmits,
            'average_throughput_bps': avg_throughput,
            'packet_loss_rate': packet_loss_rate,
            'num_successful_flows': num_successful
        }
        
        self.results['metrics'] = metrics
        
        print("\n" + "=" * 60)
        print("TEST RESULTS:")
        print("=" * 60)
        print("Total bytes transferred: {:.2f} MB".format(total_bytes / (1024.0 ** 2)))
        print("Total retransmits: {}".format(total_retransmits))
        print("Average throughput: {:.2f} Mbps".format(avg_throughput / (1024.0 ** 2)))
        print("Packet loss rate: {:.4f}".format(packet_loss_rate))
        print("Successful flows: {}/{}".format(num_successful, len(flows)))
        print("=" * 60 + "\n")
    
    def save_results(self, filename: str):
        """Save test results"""
        filepath = "../results/{}".format(filename)
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print("\u2713 Results saved to {}".format(filepath))


def main():
    parser = argparse.ArgumentParser(description='Incast Test')
    parser.add_argument('--config', default='../configs/experiment_config.json',
                       help='Configuration file')
    
    args = parser.parse_args()
    
    test = IncastTest(args.config)
    test.run_test()


if __name__ == '__main__':
    main()
