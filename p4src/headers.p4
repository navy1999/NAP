#ifndef _HEADERS_P4_
#define _HEADERS_P4_

// Type definitions
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;
typedef bit<9>  egressSpec_t;
typedef bit<16> port_t;

// Ethernet header
header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

const bit<16> TYPE_IPV4 = 0x0800;
const bit<16> TYPE_HULA = 0x1234;  // Custom ethertype for HULA probes

// IPv4 header
header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

const bit<8> TYPE_TCP = 6;
const bit<8> TYPE_UDP = 17;

// TCP header
header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<3>  res;
    bit<3>  ecn;
    bit<6>  ctrl;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

// UDP header
header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> len;
    bit<16> checksum;
}

// HULA probe header
header hula_t {
    bit<8>  type;          // Probe type (request/reply)
    bit<8>  hop_count;     // Number of hops
    bit<16> path_util;     // Path utilization metric
    bit<32> timestamp;     // Timestamp
    bit<32> dst_tor;       // Destination ToR switch ID
}

const bit<8> HULA_PROBE_REQUEST = 1;
const bit<8> HULA_PROBE_REPLY = 2;

#endif
