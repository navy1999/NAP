#include <core.p4>
#include <v1model.p4>
#include "headers.p4"

// Metadata for HULA
struct metadata {
    bit<32> switch_id;
    bit<16> path_util;
    bit<32> best_path_util;
    bit<9>  best_port;
    bit<1>  is_probe;
    bit<16> tcp_length;
}

struct headers {
    ethernet_t ethernet;
    ipv4_t     ipv4;
    tcp_t      tcp;
    udp_t      udp;
    hula_t     hula;
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
            TYPE_HULA: parse_hula;
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
    
    state parse_hula {
        packet.extract(hdr.hula);
        meta.is_probe = 1;
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
    
    // Registers for storing path utilization
    register<bit<16>>(8192) path_util_reg;
    register<bit<9>>(8192)  best_port_reg;
    
    // Drop action
    action drop() {
        mark_to_drop(standard_metadata);
    }
    
    // Forward based on flowlet table
    action set_nhop(macAddr_t dstAddr, egressSpec_t port) {
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        standard_metadata.egress_spec = port;
        if (hdr.ipv4.isValid()) {
            hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        }
    }

    // Unconditional register update for best path
    action update_best_path(bit<32> index, bit<16> util, bit<9> port) {
        path_util_reg.write(index, util);
        best_port_reg.write(index, port);
    }

    // Update HULA probe header with local info (simplified)
    action update_probe_header() {
        hdr.hula.path_util = hdr.hula.path_util + 1;
        hdr.hula.hop_count = hdr.hula.hop_count + 1;
    }
    
    // Flowlet table for data packets
    table flowlet_table {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            drop;
            set_nhop;
        }
        size = 1024;
        default_action = drop();
    }
    
    // Probe forwarding table
    table probe_fwd_table {
        key = {
            hdr.hula.dst_tor: exact;
        }
        actions = {
            drop;
            set_nhop;
        }
        size = 256;
        default_action = drop();
    }
    
    apply {
        if (meta.is_probe == 1) {
            // Handle HULA probe
            bit<32> index = hdr.hula.dst_tor;
            bit<16> current_util;
            path_util_reg.read(current_util, index);

            // Only update registers if this path is better
            if (hdr.hula.path_util < current_util) {
                update_best_path(
                    index,
                    hdr.hula.path_util,
                    (bit<9>) standard_metadata.ingress_port
                );
            }

            // Always update the probe header with local info
            update_probe_header();

            // Forward the probe according to probe_fwd_table
            probe_fwd_table.apply();

        } else if (hdr.ipv4.isValid() && hdr.ipv4.ttl > 0) {
            // Handle data packet - use best path
            bit<32> index = (bit<32>) hdr.ipv4.dstAddr;
            bit<9>  best_port;
            best_port_reg.read(best_port, index);
            
            if (best_port != 0) {
                standard_metadata.egress_spec = best_port;
                hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
            } else {
                // Fallback to flowlet table
                flowlet_table.apply();
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
    }
}

//------------------------------------------------------------------------------
// DEPARSER
//------------------------------------------------------------------------------
control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.hula);
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
