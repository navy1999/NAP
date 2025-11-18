#!/usr/bin/env python3
"""
HULA Controller - Manage probe injection and routing table updates
"""

import sys
import json
import time
import argparse
import threading
from scapy.all import Ether, Raw, sendp
from switch_manager import SwitchManager, ip_to_int, mac_to_bytes, int_to_bytes
from bm_runtime.standard.ttypes import BmMatchParam, BmMatchParamType


class HULAController:
    """Controller for HULA adaptive routing"""
    
    def __init__(self, switch_addr='localhost', thrift_port=9090):
        self.manager = SwitchManager(switch_addr, thrift_port)
        self.topology = None
        self.probe_interval = 0.1  # 100ms probe interval
        self.probe_thread = None
        self.running = False
    
    def connect(self):
        """Connect to switch"""
        return self.manager.connect()
    
    def disconnect(self):
        """Disconnect from switch"""
        self.manager.disconnect()
    
    def load_topology(self, topology_file: str):
        """Load topology configuration"""
        try:
            with open(topology_file, 'r') as f:
                self.topology = json.load(f)
            print(f"✓ Loaded topology from {topology_file}")
            return True
        except Exception as e:
            print(f"✗ Failed to load topology: {e}")
            return False
    
    def add_flowlet_entry(self, dst_prefix: str, prefix_len: int,
                         port: int, dst_mac: str):
        """
        Add flowlet table entry for destination
        
        Args:
            dst_prefix: Destination IP prefix
            prefix_len: Prefix length
            port: Egress port
            dst_mac: Destination MAC address
        """
        match_fields = [
            BmMatchParam(
                type=BmMatchParamType.LPM,
                lpm=BmMatchParamLPM(
                    key=int_to_bytes(ip_to_int(dst_prefix), 4),
                    prefix_length=prefix_len
                )
            )
        ]
        
        action_params = [
            mac_to_bytes(dst_mac),
            int_to_bytes(port, 2)
        ]
        
        return self.manager.add_table_entry(
            "flowlet_table",
            match_fields,
            "set_nhop",
            action_params
        )
    
    def add_probe_forwarding_entry(self, dst_tor_id: int, port: int, dst_mac: str):
        """
        Add probe forwarding entry
        
        Args:
            dst_tor_id: Destination ToR switch ID
            port: Egress port for probes
            dst_mac: MAC address for probes
        """
        match_fields = [
            BmMatchParam(
                type=BmMatchParamType.EXACT,
                exact=BmMatchParamExact(key=int_to_bytes(dst_tor_id, 4))
            )
        ]
        
        action_params = [
            mac_to_bytes(dst_mac),
            int_to_bytes(port, 2)
        ]
        
        return self.manager.add_table_entry(
            "probe_fwd_table",
            match_fields,
            "set_nhop",
            action_params
        )
    
    def configure_switch(self, switch_config: dict):
        """
        Configure switch with HULA routing entries
        
        Args:
            switch_config: Dictionary with switch configuration
        """
        print(f"\n=== Configuring HULA switch {switch_config['switch_id']} ===")
        
        # Add flowlet entries
        for entry in switch_config.get('flowlet_entries', []):
            prefix_parts = entry['dst_prefix'].split('/')
            dst_prefix = prefix_parts[0]
            prefix_len = int(prefix_parts[1])
            
            print(f"Adding flowlet entry for {entry['dst_prefix']}")
            self.add_flowlet_entry(
                dst_prefix,
                prefix_len,
                entry['port'],
                entry['mac']
            )
        
        # Add probe forwarding entries
        for entry in switch_config.get('probe_entries', []):
            print(f"Adding probe forwarding for ToR {entry['dst_tor_id']}")
            self.add_probe_forwarding_entry(
                entry['dst_tor_id'],
                entry['port'],
                entry['mac']
            )
        
        print(f"✓ Switch {switch_config['switch_id']} configured")
    
    def create_hula_probe(self, dst_tor_id: int, src_mac: str, dst_mac: str):
        """
        Create HULA probe packet
        
        Args:
            dst_tor_id: Destination ToR ID
            src_mac: Source MAC address
            dst_mac: Destination MAC address
        
        Returns:
            Scapy packet
        """
        # HULA probe format:
        # Ethernet (14B) | HULA header (12B)
        # HULA: type(1B) | hop_count(1B) | path_util(2B) | timestamp(4B) | dst_tor(4B)
        
        hula_header = bytes([
            1,              # type = PROBE_REQUEST
            0,              # hop_count = 0
            0, 0,           # path_util = 0
        ]) + int_to_bytes(int(time.time()), 4) + int_to_bytes(dst_tor_id, 4)
        
        pkt = Ether(src=src_mac, dst=dst_mac, type=0x1234) / Raw(load=hula_header)
        return pkt
    
    def inject_probes(self, interface: str, probe_config: dict):
        """
        Periodically inject HULA probes
        
        Args:
            interface: Network interface to send probes on
            probe_config: Configuration for probe injection
        """
        print(f"\n=== Starting probe injection on {interface} ===")
        
        while self.running:
            for probe in probe_config.get('probes', []):
                pkt = self.create_hula_probe(
                    probe['dst_tor_id'],
                    probe['src_mac'],
                    probe['dst_mac']
                )
                sendp(pkt, iface=interface, verbose=False)
            
            time.sleep(self.probe_interval)
    
    def start_probe_injection(self, interface: str, probe_config: dict):
        """Start probe injection in background thread"""
        self.running = True
        self.probe_thread = threading.Thread(
            target=self.inject_probes,
            args=(interface, probe_config)
        )
        self.probe_thread.daemon = True
        self.probe_thread.start()
        print("✓ Probe injection started")
    
    def stop_probe_injection(self):
        """Stop probe injection"""
        self.running = False
        if self.probe_thread:
            self.probe_thread.join()
        print("✓ Probe injection stopped")
    
    def monitor_path_utilization(self, duration: int = 60):
        """
        Monitor and display path utilization from registers
        
        Args:
            duration: Monitoring duration in seconds
        """
        print(f"\n=== Monitoring path utilization for {duration}s ===")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            print("\nCurrent path utilization:")
            for tor_id in range(1, 4):  # Assume 3 ToR switches
                util = self.manager.read_register("path_util_reg", tor_id)
                port = self.manager.read_register("best_port_reg", tor_id)
                print(f"  ToR {tor_id}: util={util}, best_port={port}")
            
            time.sleep(5)
    
    def clear_all_tables(self):
        """Clear all HULA tables"""
        print("\n=== Clearing all tables ===")
        self.manager.clear_table("flowlet_table")
        self.manager.clear_table("probe_fwd_table")


def main():
    parser = argparse.ArgumentParser(description='HULA Controller')
    parser.add_argument('--switch', default='localhost',
                       help='Switch IP address')
    parser.add_argument('--port', type=int, default=9090,
                       help='Thrift port')
    parser.add_argument('--topology', default='../configs/topology.json',
                       help='Topology configuration file')
    parser.add_argument('--interface', default='veth0',
                       help='Interface for probe injection')
    parser.add_argument('--probe-interval', type=float, default=0.1,
                       help='Probe injection interval (seconds)')
    parser.add_argument('--monitor', type=int, default=0,
                       help='Monitor duration (seconds, 0=no monitoring)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear all tables before configuring')
    
    args = parser.parse_args()
    
    controller = HULAController(args.switch, args.port)
    controller.probe_interval = args.probe_interval
    
    if not controller.connect():
        sys.exit(1)
    
    if args.clear:
        controller.clear_all_tables()
    
    if controller.load_topology(args.topology):
        # Configure switch
        for switch in controller.topology.get('switches', []):
            controller.configure_switch(switch)
        
        # Start probe injection if configured
        probe_config = controller.topology.get('probe_config', {})
        if probe_config and args.interface:
            controller.start_probe_injection(args.interface, probe_config)
        
        # Monitor if requested
        if args.monitor > 0:
            try:
                controller.monitor_path_utilization(args.monitor)
            except KeyboardInterrupt:
                print("\nMonitoring interrupted")
        
        controller.stop_probe_injection()
    
    controller.disconnect()


if __name__ == '__main__':
    main()
