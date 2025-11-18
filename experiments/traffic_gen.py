#!/usr/bin/env python3
"""
Traffic generator using iperf3
"""

import subprocess
import time

class TrafficGenerator:
    def __init__(self, hosts):
        self.hosts = hosts
    
    def run_iperf_server(self, host):
        """Start iperf3 server on host"""
        cmd = f"iperf3 -s -D"
        subprocess.run(cmd.split())
    
    def run_iperf_client(self, src, dst, duration=10, bandwidth='10M'):
        """Run iperf3 client from src to dst"""
        cmd = f"iperf3 -c {dst} -t {duration} -b {bandwidth} -J"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return result.stdout
    
    def incast_pattern(self, senders, receiver, duration=10):
        """Generate incast traffic pattern"""
        results = []
        for sender in senders:
            result = self.run_iperf_client(sender, receiver, duration)
            results.append(result)
        return results

if __name__ == '__main__':
    gen = TrafficGenerator(['h1_1', 'h1_2', 'h2_1'])
    gen.incast_pattern(['h1_1', 'h1_2'], 'h2_1')
