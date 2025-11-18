#!/usr/bin/env python3
"""
Link failure scenario - Test recovery from link failures
Simulates dynamic network conditions
"""

import sys
import time
import argparse
import json
import subprocess
from datetime import datetime
from traffic_gen import TrafficGenerator


class LinkFailureTest:
    """Link failure and recovery test"""
    
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)
        self.traffic_gen = TrafficGenerator()
        self.results = {
            'test_type': 'link_failure',
            'timestamp': datetime.now().isoformat(),
            'phases': []
        }
    
    def load_config(self, config_file: str) -> dict:
        """Load test configuration"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def bring_link_down(self, switch: str, port: int):
        """
        Bring a switch link down
        
        Args:
            switch: Switch name (e.g., 's1')
            port: Port number
        """
        print(f"\n✗ Bringing link down: {switch} port {port}")
        
        # In Mininet: net.configLinkStatus(switch, other_switch, 'down')
        # For simulation, we'll use a placeholder command
        cmd = f"ovs-ofctl mod-port {switch} {port} down"
        
        try:
            subprocess.run(cmd.split(), check=True, capture_output=True)
            self.results['phases'].append({
                'timestamp': time.time(),
                'event': 'link_down',
                'switch': switch,
                'port': port
            })
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to bring link down: {e}")
            return False
    
    def bring_link_up(self, switch: str, port: int):
        """
        Bring a switch link up
        
        Args:
            switch: Switch name
            port: Port number
        """
        print(f"\n✓ Bringing link up: {switch} port {port}")
        
        cmd = f"ovs-ofctl mod-port {switch} {port} up"
        
        try:
            subprocess.run(cmd.split(), check=True, capture_output=True)
            self.results['phases'].append({
                'timestamp': time.time(),
                'event': 'link_up',
                'switch': switch,
                'port': port
            })
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to bring link up: {e}")
            return False
    
    def measure_flow(self, src: str, dst: str, duration: int, 
                    phase_name: str) -> dict:
        """
        Measure a single flow during a test phase
        
        Args:
            src: Source host
            dst: Destination host
            duration: Flow duration
            phase_name: Name of test phase
        
        Returns:
            Flow measurement results
        """
        print(f"  Measuring flow: {src} → {dst} ({duration}s)")
        
        result = self.traffic_gen.run_iperf_client(
            src, dst, duration=duration, bandwidth='100M'
        )
        
        result['phase'] = phase_name
        result['measurement_time'] = time.time()
        
        return result
    
    def run_test(self):
        """Execute link failure test"""
        print(f"\n{'='*60}")
        print(f"LINK FAILURE TEST")
        print(f"{'='*60}\n")
        
        # Test configuration
        src = "10.0.1.1"
        dst = "10.0.2.1"
        phase_duration = 30
        
        # Start receiver
        self.traffic_gen.start_iperf_server(dst)
        time.sleep(2)
        
        # Phase 1: Normal operation (baseline)
        print("\n[Phase 1: Baseline - Normal Operation]")
        phase1_result = self.measure_flow(src, dst, phase_duration, "baseline")
        self.results['phases'].append({
            'phase': 'baseline',
            'flow_result': phase1_result
        })
        
        time.sleep(5)
        
        # Phase 2: Link failure
        print("\n[Phase 2: Link Failure]")
        self.bring_link_down('s1', 2)  # Bring down link between s1 and spine
        time.sleep(2)  # Wait for failure detection
        
        phase2_result = self.measure_flow(src, dst, phase_duration, "failure")
        self.results['phases'].append({
            'phase': 'failure',
            'flow_result': phase2_result
        })
        
        time.sleep(5)
        
        # Phase 3: Link recovery
        print("\n[Phase 3: Link Recovery]")
        self.bring_link_up('s1', 2)
        time.sleep(2)  # Wait for reconvergence
        
        phase3_result = self.measure_flow(src, dst, phase_duration, "recovery")
        self.results['phases'].append({
            'phase': 'recovery',
            'flow_result': phase3_result
        })
        
        # Calculate metrics
        self.calculate_metrics()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"link_failure_results_{timestamp}.json"
        self.save_results(results_file)
    
    def calculate_metrics(self):
        """Calculate recovery metrics"""
        phases = [p for p in self.results['phases'] if 'flow_result' in p]
        
        if len(phases) < 3:
            print("Insufficient data for analysis")
            return
        
        baseline = phases[0]['flow_result']
        failure = phases[1]['flow_result']
        recovery = phases[2]['flow_result']
        
        baseline_throughput = baseline.get('bits_per_second', 0)
        failure_throughput = failure.get('bits_per_second', 0)
        recovery_throughput = recovery.get('bits_per_second', 0)
        
        metrics = {
            'baseline_throughput_mbps': baseline_throughput / (1024**2),
            'failure_throughput_mbps': failure_throughput / (1024**2),
            'recovery_throughput_mbps': recovery_throughput / (1024**2),
            'throughput_degradation_pct': (1 - failure_throughput / max(baseline_throughput, 1)) * 100,
            'recovery_efficiency_pct': (recovery_throughput / max(baseline_throughput, 1)) * 100,
            'baseline_retransmits': baseline.get('retransmits', 0),
            'failure_retransmits': failure.get('retransmits', 0),
            'recovery_retransmits': recovery.get('retransmits', 0)
        }
        
        self.results['metrics'] = metrics
        
        print("\n" + "="*60)
        print("TEST RESULTS:")
        print("="*60)
        print(f"Baseline throughput: {metrics['baseline_throughput_mbps']:.2f} Mbps")
        print(f"Failure throughput: {metrics['failure_throughput_mbps']:.2f} Mbps")
        print(f"Recovery throughput: {metrics['recovery_throughput_mbps']:.2f} Mbps")
        print(f"Throughput degradation: {metrics['throughput_degradation_pct']:.1f}%")
        print(f"Recovery efficiency: {metrics['recovery_efficiency_pct']:.1f}%")
        print(f"Retransmits - Baseline: {metrics['baseline_retransmits']}, "
              f"Failure: {metrics['failure_retransmits']}, "
              f"Recovery: {metrics['recovery_retransmits']}")
        print("="*60 + "\n")
    
    def save_results(self, filename: str):
        """Save test results"""
        filepath = f"../results/{filename}"
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✓ Results saved to {filepath}")


def main():
    parser = argparse.ArgumentParser(description='Link Failure Test')
    parser.add_argument('--config', default='../configs/experiment_config.json',
                       help='Configuration file')
    
    args = parser.parse_args()
    
    test = LinkFailureTest(args.config)
    test.run_test()


if __name__ == '__main__':
    main()
