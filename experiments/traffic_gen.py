#!/usr/bin/env python3
"""
Advanced traffic generator with multiple patterns and logging
"""

import subprocess
import time
import json
import os
from typing import List, Dict
from datetime import datetime


class TrafficGenerator:
    """Generate various traffic patterns for testing"""
    
    def __init__(self, log_dir='../logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.results = []
    
    def _log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        log_file = os.path.join(self.log_dir, 'traffic_gen.log')
        with open(log_file, 'a') as f:
            f.write(log_msg + '\n')
    
    def start_iperf_server(self, host: str, port: int = 5201):
        """
        Start iperf3 server on host
        
        Args:
            host: Host name/IP
            port: iperf3 port (default 5201)
        
        Returns:
            subprocess.Popen object
        """
        cmd = f"iperf3 -s -p {port} -D"
        self._log(f"Starting iperf3 server on {host}:{port}")
        
        # In real Mininet, you would use net.get(host).cmd()
        # For now, using subprocess as placeholder
        proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        time.sleep(1)  # Wait for server to start
        return proc
    
    def run_iperf_client(self, src: str, dst: str, dst_port: int = 5201,
                        duration: int = 10, bandwidth: str = '10M',
                        protocol: str = 'tcp') -> Dict:
        """
        Run iperf3 client from src to dst
        
        Args:
            src: Source host
            dst: Destination host IP
            dst_port: Destination port
            duration: Test duration in seconds
            bandwidth: Target bandwidth (e.g., '10M', '100M', '1G')
            protocol: 'tcp' or 'udp'
        
        Returns:
            Dictionary with results
        """
        cmd = f"iperf3 -c {dst} -p {dst_port} -t {duration} -b {bandwidth} -J"
        if protocol == 'udp':
            cmd += " -u"
        
        self._log(f"Running iperf3: {src} → {dst} ({bandwidth}, {duration}s)")
        
        try:
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=duration + 10
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                summary = {
                    'src': src,
                    'dst': dst,
                    'duration': duration,
                    'bandwidth_requested': bandwidth,
                    'bytes_transferred': data['end']['sum_sent']['bytes'],
                    'bits_per_second': data['end']['sum_sent']['bits_per_second'],
                    'retransmits': data['end']['sum_sent'].get('retransmits', 0),
                    'timestamp': datetime.now().isoformat()
                }
                self.results.append(summary)
                return summary
            else:
                self._log(f"iperf3 failed: {result.stderr}")
                return {'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            self._log(f"iperf3 timeout from {src} to {dst}")
            return {'error': 'timeout'}
        except json.JSONDecodeError as e:
            self._log(f"Failed to parse iperf3 output: {e}")
            return {'error': 'parse_error'}
    
    def incast_pattern(self, senders: List[str], receiver: str,
                      duration: int = 10, bandwidth: str = '10M') -> List[Dict]:
        """
        Generate incast traffic pattern (many-to-one)
        
        Args:
            senders: List of sender hosts
            receiver: Receiver host IP
            duration: Flow duration
            bandwidth: Per-flow bandwidth
        
        Returns:
            List of result dictionaries
        """
        self._log(f"=== Starting incast: {len(senders)} → 1 ===")
        
        # Start server on receiver
        self.start_iperf_server(receiver)
        time.sleep(2)
        
        # Start all senders simultaneously
        results = []
        for sender in senders:
            result = self.run_iperf_client(
                sender, receiver, duration=duration, bandwidth=bandwidth
            )
            results.append(result)
        
        self._log(f"=== Incast complete ===")
        return results
    
    def stride_pattern(self, hosts: List[str], stride: int = 1,
                      duration: int = 10, bandwidth: str = '10M') -> List[Dict]:
        """
        Generate stride traffic pattern
        
        Args:
            hosts: List of hosts
            stride: Stride length for destination selection
            duration: Flow duration
            bandwidth: Per-flow bandwidth
        
        Returns:
            List of results
        """
        self._log(f"=== Starting stride pattern (stride={stride}) ===")
        
        results = []
        n = len(hosts)
        
        for i, src in enumerate(hosts):
            dst_idx = (i + stride) % n
            dst = hosts[dst_idx]
            
            # Start server on destination
            self.start_iperf_server(dst)
            time.sleep(1)
            
            # Run client
            result = self.run_iperf_client(
                src, dst, duration=duration, bandwidth=bandwidth
            )
            results.append(result)
        
        self._log(f"=== Stride pattern complete ===")
        return results
    
    def random_pattern(self, hosts: List[str], num_flows: int = 10,
                      duration: int = 10, bandwidth: str = '10M') -> List[Dict]:
        """
        Generate random traffic pattern
        
        Args:
            hosts: List of hosts
            num_flows: Number of random flows to generate
            duration: Flow duration
            bandwidth: Per-flow bandwidth
        
        Returns:
            List of results
        """
        import random
        
        self._log(f"=== Starting random pattern ({num_flows} flows) ===")
        
        results = []
        for _ in range(num_flows):
            src, dst = random.sample(hosts, 2)
            
            self.start_iperf_server(dst)
            time.sleep(1)
            
            result = self.run_iperf_client(
                src, dst, duration=duration, bandwidth=bandwidth
            )
            results.append(result)
        
        self._log(f"=== Random pattern complete ===")
        return results
    
    def save_results(self, filename: str):
        """Save all results to JSON file"""
        filepath = os.path.join(self.log_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        self._log(f"Results saved to {filepath}")


if __name__ == '__main__':
    # Example usage
    gen = TrafficGenerator()
    
    # Define test hosts
    senders = ['10.0.1.1', '10.0.1.2', '10.0.1.3']
    receiver = '10.0.2.1'
    
    # Run incast test
    results = gen.incast_pattern(senders, receiver, duration=30, bandwidth='50M')
    
    # Save results
    gen.save_results('incast_results.json')
