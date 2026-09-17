import socket
import json
import threading


def discover_server(timeout=5, broadcast_port=8765, on_found=None, on_timeout=None):
    """
    监听局域网广播，自动发现服务器地址
    on_found(url)  - 找到服务器时回调
    on_timeout()   - 超时未找到时回调
    """
    def listen():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        try:
            sock.bind(("", broadcast_port))
            while True:
                try:
                    data, _ = sock.recvfrom(1024)
                    message = json.loads(data.decode("utf-8"))
                    if message.get("service") == "nongzhi_api":
                        ip = message["ip"]
                        port = message["port"]
                        url = f"http://{ip}:{port}"
                        if callable(on_found):
                            on_found(url)
                        return
                except socket.timeout:
                    if callable(on_timeout):
                        on_timeout()
                    return
                except Exception:
                    continue
        finally:
            sock.close()

    t = threading.Thread(target=listen, daemon=True)
    t.start()
