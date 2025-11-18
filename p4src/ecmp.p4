#include <core.p4>
#include <v1model.p4>
#include "headers.p4"

// Metadata for ECMP
struct metadata {
    bit<14> ecmp_hash;
    bit<14> ecmp_group_id;
    bit<16> tcp_length;
}

struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;
    tcp_t      tcp;
    udp_t      udp;
}

//------------------------------------------------------------------------------
// PARSER
//------------------------------------------------------------------------------
parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    
    state start {
        transition parse_ethernet;
    }
    
    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }
    
    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        meta.tcp_length = hdr.ipv4.totalLen - 16w20;
        transition select(hdr.ipv4.protocol) {
            TYPE_TCP: parse_tcp;
            TYPE_UDP: parse_udp;
            default: accept;
        }
    }
    
    state parse_tcp {
        packet.extract(hdr.tcp);
        transition accept;
    }
    
    state parse_udp {
        packet.extract(hdr.udp);
        transition accept;
    }
}

//------------------------------------------------------------------------------
// CHECKSUM VERIFICATION
//------------------------------------------------------------------------------
control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

//------------------------------------------------------------------------------
// INGRESS PROCESSING
//------------------------------------------------------------------------------
control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    
    // Drop action
    action drop() {
        mark_to_drop(standard_metadata);
    }
    
    // Set ECMP group for destination
    action set_ecmp_group(bit<14> ecmp_group_id, bit<16> num_nhops) {
        meta.ecmp_group_id = ecmp_group_id;
        
        // Compute hash based on 5-tuple
        hash(meta.ecmp_hash,
             HashAlgorithm.crc16,
             (bit<1>)0,
             { hdr.ipv4.srcAddr,
               hdr.ipv4.dstAddr,
               hdr.ipv4.protocol,
               hdr.tcp.isValid() ? hdr.tcp.srcPort : 16w0,
               hdr.tcp.isValid() ? hdr.tcp.dstPort : 16w0,
               hdr.udp.isValid() ? hdr.udp.srcPort : 16w0,
               hdr.udp.isValid() ? hdr.udp.dstPort : 16w0 },
             num_nhops);
    }
    
    // Set next hop based on hash
    action set_nhop(macAddr_t dstAddr, egressSpec_t port) {
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }
    
    // ECMP group table
    table ecmp_group {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            drop;
            set_ecmp_group;
        }
        size = 1024;
        default_action = drop();
    }
    
    // Next hop selection table
    table ecmp_nhop {
        key = {
            meta.ecmp_group_id: exact;
            meta.ecmp_hash: exact;
        }
        actions = {
            drop;
            set_nhop;
        }
        size = 16384;
        default_action = drop();
    }
    
    apply {
        if (hdr.ipv4.isValid() && hdr.ipv4.ttl > 0) {
            // First determine ECMP group
            if (ecmp_group.apply().hit) {
                // Then select next hop based on hash
                ecmp_nhop.apply();
            }
        }
    }
}

//------------------------------------------------------------------------------
// EGRESS PROCESSING
//------------------------------------------------------------------------------
control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    apply { }
}

//------------------------------------------------------------------------------
// CHECKSUM COMPUTATION
//------------------------------------------------------------------------------
control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version,
              hdr.ipv4.ihl,
              hdr.ipv4.diffserv,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
        
        update_checksum_with_payload(
            hdr.tcp.isValid(),
            { hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr,
              8w0,
              hdr.ipv4.protocol,
              meta.tcp_length,
              hdr.tcp.srcPort,
              hdr.tcp.dstPort,
              hdr.tcp.seqNo,
              hdr.tcp.ackNo,
              hdr.tcp.dataOffset,
              hdr.tcp.res,
              hdr.tcp.ecn,
              hdr.tcp.ctrl,
              hdr.tcp.window,
              hdr.tcp.urgentPtr },
            hdr.tcp.checksum,
            HashAlgorithm.csum16);
    }
}

//------------------------------------------------------------------------------
// DEPARSER
//------------------------------------------------------------------------------
control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.tcp);
        packet.emit(hdr.udp);
    }
}

//------------------------------------------------------------------------------
// SWITCH
//------------------------------------------------------------------------------
V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
