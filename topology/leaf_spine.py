#!/usr/bin/env python3
"""
Leaf-spine topology for P4 experiments
2 spines, 3 leaves, 24 hosts per leaf
"""

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.cli import CLI

class LeafSpineTopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        
        # Create spines
        spines = []
        for i in range(1, 3):
            spine = self.addSwitch(f's{i}')
            spines.append(spine)
        
        # Create leaves and hosts
        for i in range(1, 4):
            leaf = self.addSwitch(f'l{i}')
            
            # Connect leaf to all spines
            for spine in spines:
                self.addLink(leaf, spine)
            
            # Add hosts to leaf
            for j in range(1, 25):
                host = self.addHost(f'h{i}_{j}')
                self.addLink(host, leaf)

def main():
    setLogLevel('info')
    topo = LeafSpineTopo()
    net = Mininet(topo=topo)
    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    main()
