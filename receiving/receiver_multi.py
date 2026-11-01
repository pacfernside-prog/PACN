import socket
import struct
import itertools

import pacn.utils as UT

# NOTE: This file was never finished or tested.
# It is not used by any other code in PACN

MCAST_GRP = '239.255.0.0'
PORT = 5568

def universes(data: bytes) -> list[int]:
    x = []
    for i in itertools.batched(data[120:], 2):
        print(i)
        x.append(UT.bytes_to_int(bytes(i)))
    return x

def start_e131_discovery_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # Configure port reuse so multiple test utilities can listen
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    # Bind to the E1.31 port across all interfaces
    sock.bind(('', PORT))
    
    # join the E1.31 Discovery multicast group
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            
            # E1.31 packet parsing context 
            print(f"Received E1.31 packet ({len(data)} bytes) from {addr}")
            
            # Basic Hex inspect to verify sACN ACN Root Layer framing
            if len(data) > 6 and data[4:6] == b'\x00\x10':
                print(" -> Valid sACN / ACN Preamble detected.")
            else:
                print(f" -> Raw Payload Header: {data[:20].hex().upper()}")
            ux = universes(data)
            print("Universes", ux, data[120:], len(data))
                
    except KeyboardInterrupt:
        print("\nStopping E1.31 receiver...")
    finally:
        sock.close()

if __name__ == "__main__":
    start_e131_discovery_receiver()
