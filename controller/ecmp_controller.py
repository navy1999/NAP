#!/usr/bin/env python3
"""
ECMP Controller - Populate routing tables for ECMP load balancing
"""

import sys
import json
import argparse
from switch_manager import SwitchManager, ip_to_int, mac_to_bytes, int_to_bytes
from bm_runtime.standard.ttypes import BmMatchParam, BmMatchParamType


class ECMPController:
    """Controller for ECMP switch configuration"""
    
    def __init__(self, switch_addr='localhost', thrift_port=9090):
        self.manager = SwitchManager(switch_addr, thrift_port)
        self.topology = None
    
    def connect(self):
        """Connect to switch"""
        return self.manager.connect()
    
    def disconnect(self):
        """Disconnect from switch"""
        self.manager.disconnect()
    
    def load_topology(self, topology_file: str):
        """Load topology configuration from JSON file"""
        try:
            with open(topology_file, 'r') as f:
                self.topology = json.load(f)
            print(f"✓ Loaded topology from {topology_file}")
            return True
        except Exception as e:
            print(f"✗ Failed to load topology: {e}")
            return False
    
    def add_ecmp_group(self, dst_prefix: str, prefix_len: int, 
                       group_id: int, num_paths: int):
        """
        Add ECMP group entry for destination prefix
        
        Args:
            dst_prefix: Destination IP prefix (e.g., "10.0.1.0")
            prefix_len: Prefix length (e.g., 24)
            group_id: ECMP group ID
            num_paths: Number of equal-cost paths
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
            int_to_bytes(group_id, 2),      # ecmp_group_id (14 bits, use 2 bytes)
            int_to_bytes(num_paths, 2)       # num_nhops
        ]
        
        return self.manager.add_table_entry(
            "ecmp_group",
            match_fields,
            "set_ecmp_group",
            action_params
        )
    
    def add_next_hop(self, group_id: int, hash_val: int, 
                     port: int, dst_mac: str):
        """
        Add next-hop entry for ECMP group
        
        Args:
            group_id: ECMP group ID
            hash_val: Hash value (0 to num_paths-1)
            port: Egress port
            dst_mac: Destination MAC address
        """
        match_fields = [
            BmMatchParam(
                type=BmMatchParamType.EXACT,
                exact=BmMatchParamExact(key=int_to_bytes(group_id, 2))
            ),
            BmMatchParam(
                type=BmMatchParamType.EXACT,
                exact=BmMatchParamExact(key=int_to_bytes(hash_val, 2))
            )
        ]
        
        action_params = [
            mac_to_bytes(dst_mac),           # dstAddr
            int_to_bytes(port, 2)            # port (9 bits, use 2 bytes)
        ]
        
        return self.manager.add_table_entry(
            "ecmp_nhop",
            match_fields,
            "set_nhop",
            action_params
        )
    
    def configure_switch(self, switch_config: dict):
        """
        Configure switch with ECMP groups and next hops
        
        Args:
            switch_config: Dictionary with switch configuration
                {
                    "switch_id": "s1",
                    "ecmp_groups": [
                        {
                            "dst_prefix": "10.0.1.0/24",
                            "group_id": 1,
                            "next_hops": [
                                {"port": 1, "mac": "00:00:00:00:01:01"},
                                {"port": 2, "mac": "00:00:00:00:01:02"}
                            ]
                        }
                    ]
                }
        """
        print(f"\n=== Configuring switch {switch_config['switch_id']} ===")
        
        for group in switch_config.get('ecmp_groups', []):
            # Parse prefix
            prefix_parts = group['dst_prefix'].split('/')
            dst_prefix = prefix_parts[0]
            prefix_len = int(prefix_parts[1])
            
            group_id = group['group_id']
            next_hops = group['next_hops']
            num_paths = len(next_hops)
            
            # Add ECMP group
            print(f"\nAdding ECMP group {group_id} for {group['dst_prefix']}")
            self.add_ecmp_group(dst_prefix, prefix_len, group_id, num_paths)
            
            # Add next hops
            for idx, nhop in enumerate(next_hops):
                print(f"  Next hop {idx}: port={nhop['port']}, mac={nhop['mac']}")
                self.add_next_hop(
                    group_id, 
                    idx, 
                    nhop['port'], 
                    nhop['mac']
                )
        
        print(f"\n✓ Switch {switch_config['switch_id']} configured")
    
    def populate_from_topology(self):
        """Populate all switches from loaded topology"""
        if not self.topology:
            print("✗ No topology loaded")
            return False
        
        for switch in self.topology.get('switches', []):
            if not self.connect():
                continue
            
            self.configure_switch(switch)
            self.disconnect()
            
        return True
    
    def clear_all_tables(self):
        """Clear all ECMP tables"""
        print("\n=== Clearing all tables ===")
        self.manager.clear_table("ecmp_group")
        self.manager.clear_table("ecmp_nhop")


def main():
    parser = argparse.ArgumentParser(description='ECMP Controller')
    parser.add_argument('--switch', default='localhost', 
                       help='Switch IP address')
    parser.add_argument('--port', type=int, default=9090,
                       help='Thrift port')
    parser.add_argument('--topology', default='../configs/topology.json',
                       help='Topology configuration file')
    parser.add_argument('--clear', action='store_true',
                       help='Clear all tables before configuring')
    
    args = parser.parse_args()
    
    controller = ECMPController(args.switch, args.port)
    
    if not controller.connect():
        sys.exit(1)
    
    if args.clear:
        controller.clear_all_tables()
    
    if controller.load_topology(args.topology):
        controller.populate_from_topology()
    
    controller.disconnect()


if __name__ == '__main__':
    main()
