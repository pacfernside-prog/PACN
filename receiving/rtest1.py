from pacn.receiving.receiver_udp import Receiver
from pacn.receiving.receiver_data import decode_packet

def main() -> None:
    with Receiver() as rvr:
        while True:
            x = rvr.get_packet()
            if x is None:
                break
            # print("Got packet", x)
            try:
                pkt = decode_packet(x)
            except ValueError as ve:
                print(ve)
            else:
                if pkt is not None:
                    print(pkt.universe)

if __name__ == "__main__":
    main()
