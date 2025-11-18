#!/usr/bin/env python3
"""
Switch manager utility for BMv2 Thrift API
Handles connection and common operations
"""

import sys
import time
from typing import List, Dict, Any

# Add runtime_CLI path for BMv2 Thrift bindings
sys.path.append('/usr/local/lib/python3.8/site-packages')

try:
    from thrift.transport import TSocket
    from thrift.transport import TTransport
    from thrift.protocol import TBinaryProtocol
    from bm_runtime.standard import Standard
    from bm_runtime.standard.ttypes import *
except ImportError as e:
    print(f"Error importing Thrift: {e}")
    print("Make sure BMv2 is installed with Python bindings")
    sys.exit(1)


class SwitchManager:
    """Manages connection and operations on a BMv2 switch via Thrift"""
    
    def __init__(self, thrift_ip='localhost', thrift_port=9090):
        self.thrift_ip = thrift_ip
        self.thrift_port = thrift_port
        self.client = None
        self.transport = None
    
    def connect(self):
        """Establish Thrift connection to switch"""
        try:
            transport = TSocket.TSocket(self.thrift_ip, self.thrift_port)
            transport = TTransport.TBufferedTransport(transport)
            bprotocol = TBinaryProtocol.TBinaryProtocol(transport)
            
            self.client = Standard.Client(bprotocol)
            self.transport = transport
            transport.open()
            print(f"✓ Connected to switch at {self.thrift_ip}:{self.thrift_port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Close Thrift connection"""
        if self.transport:
            self.transport.close()
            print("✓ Disconnected from switch")
    
    def add_table_entry(self, table_name: str, match_fields: List, 
                       action_name: str, action_params: List):
        """
        Add entry to a table
        
        Args:
            table_name: Name of the table
            match_fields: List of BmMatchParam objects
            action_name: Name of the action
            action_params: List of action parameter values
        """
        try:
            self.client.bm_mt_add_entry(
                0,  # cxt_id (context ID, usually 0)
                table_name,
                match_fields,
                action_name,
                action_params,
                BmAddEntryOptions()
            )
            print(f"✓ Added entry to table '{table_name}'")
            return True
        except Exception as e:
            print(f"✗ Failed to add entry to '{table_name}': {e}")
            return False
    
    def delete_table_entry(self, table_name: str, entry_handle: int):
        """Delete entry from table by handle"""
        try:
            self.client.bm_mt_delete_entry(0, table_name, entry_handle)
            print(f"✓ Deleted entry from table '{table_name}'")
            return True
        except Exception as e:
            print(f"✗ Failed to delete entry: {e}")
            return False
    
    def clear_table(self, table_name: str):
        """Clear all entries from a table"""
        try:
            self.client.bm_mt_clear_entries(0, table_name, False)
            print(f"✓ Cleared table '{table_name}'")
            return True
        except Exception as e:
            print(f"✗ Failed to clear table: {e}")
            return False
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the switch"""
        try:
            return self.client.bm_get_tables()
        except Exception as e:
            print(f"✗ Failed to get tables: {e}")
            return []
    
    def set_default_action(self, table_name: str, action_name: str, 
                          action_params: List):
        """Set default action for a table"""
        try:
            self.client.bm_mt_set_default_action(
                0, table_name, action_name, action_params
            )
            print(f"✓ Set default action for '{table_name}' to '{action_name}'")
            return True
        except Exception as e:
            print(f"✗ Failed to set default action: {e}")
            return False
    
    def read_register(self, register_name: str, index: int) -> int:
        """Read value from register at index"""
        try:
            return self.client.bm_register_read(0, register_name, index)
        except Exception as e:
            print(f"✗ Failed to read register: {e}")
            return -1
    
    def write_register(self, register_name: str, index: int, value: int):
        """Write value to register at index"""
        try:
            self.client.bm_register_write(0, register_name, index, value)
            return True
        except Exception as e:
            print(f"✗ Failed to write register: {e}")
            return False


def ip_to_int(ip_str: str) -> int:
    """Convert IP string to integer"""
    parts = ip_str.split('.')
    return (int(parts[0]) << 24) + (int(parts[1]) << 16) + \
           (int(parts[2]) << 8) + int(parts[3])


def mac_to_bytes(mac_str: str) -> bytes:
    """Convert MAC string to bytes"""
    return bytes.fromhex(mac_str.replace(':', ''))


def int_to_bytes(num: int, num_bytes: int) -> bytes:
    """Convert integer to bytes with specific length"""
    return num.to_bytes(num_bytes, byteorder='big')
