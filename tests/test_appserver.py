from __future__ import annotations

import json

import pytest

from codex_auto_continuer.appserver import AppServerClient, RpcError
from codex_auto_continuer.errors import ProtocolError


class FakeWS:
    def __init__(self, incoming):
        self.incoming = list(incoming)
        self.sent = []
        self.closed = False
    def send_text(self, text): self.sent.append(json.loads(text))
    def begin_request(self): pass
    def recv_text(self): return json.dumps(self.incoming.pop(0))
    def close(self): self.closed = True


def test_request_ignores_notifications_and_never_answers_server_request():
    ws = FakeWS([
        {"method":"thread/status/changed","params":{}},
        {"id":99,"method":"item/commandExecution/requestApproval","params":{}},
        {"id":1,"result":{"ok":True}},
    ])
    client = AppServerClient(ws)
    assert client.request("x", {}) == {"ok":True}
    assert len(ws.sent) == 1
    assert client.server_requests[0]["id"] == 99
    assert client.notifications[0]["method"] == "thread/status/changed"
    assert client.next_notification()["id"] == 99  # Observer must see buffered input requests too.
    assert len(ws.sent) == 1


def test_rpc_error_is_precise():
    client = AppServerClient(FakeWS([{"id":1,"error":{"code":-1,"message":"no"}}]))
    with pytest.raises(RpcError, match="Codex RPC x failed"):
        client.request("x", {})


def test_rpc_error_diagnostic_does_not_leak_server_body():
    error = RpcError("thread/queue/add", {"code": -32600, "message": "private conversation body"})
    assert "private conversation body" not in str(error)
    assert "-32600" in str(error)


def test_wrong_response_id_fails():
    client = AppServerClient(FakeWS([{"id":2,"result":{}}]))
    with pytest.raises(ProtocolError, match="expected 1"):
        client.request("x", {})


def test_initialize_failure_closes_transport(monkeypatch, tmp_path):
    from codex_auto_continuer.ws_unix import UnixWebSocket
    ws = FakeWS([{"id": 1, "error": {"code": -1, "message": "unsupported"}}])
    monkeypatch.setattr(UnixWebSocket, "connect", lambda *_: ws)
    with pytest.raises(RpcError):
        AppServerClient.connect(tmp_path / "fixture.sock", 1)
    assert ws.closed


def test_notifications_cannot_extend_total_rpc_deadline():
    import socket
    import time
    from codex_auto_continuer.ws_unix import UnixWebSocket
    from codex_auto_continuer.errors import TransportError
    from test_ws_unix import server_frame
    a, b = socket.socketpair()
    a.settimeout(0.03)
    ws = UnixWebSocket(a)
    original = ws.recv_text
    def receive():
        b.sendall(server_frame(1, b'{"method":"noise"}'))
        time.sleep(0.015)
        return original()
    ws.recv_text = receive
    try:
        with pytest.raises(TransportError, match="deadline"):
            AppServerClient(ws).request("neverResponds", {})
    finally:
        ws.close()
        b.close()


def test_queue_items_paginates():
    client = AppServerClient(FakeWS([
        {"id":1,"result":{"data":[{"id":"a"}],"nextCursor":"c"}},
        {"id":2,"result":{"data":[{"id":"b"}],"nextCursor":None}},
    ]))
    assert [x["id"] for x in client.queue_items("t")] == ["a","b"]


def test_resume_tracks_subscription():
    client = AppServerClient(FakeWS([{"id":1,"result":{"thread":{"id":"t"}}}]))
    client.resume_thread("t")
    assert client.thread_subscriptions == {"t"}
    client.close()
    assert not client.thread_subscriptions

def test_queue_delete_requires_boolean_deleted():
    client = AppServerClient(FakeWS([{"id":1,"result":{"deleted":True}}]))
    assert client.queue_delete("t","q") is True
    assert client._ws.sent[0]["params"] == {"threadId":"t","queuedSubmissionId":"q"}

def test_connect_performs_real_unix_websocket_initialize(unix_path, unix_listener):
    import base64
    import hashlib
    import socket
    import struct
    import threading
    from codex_auto_continuer.ws_unix import _GUID

    path = unix_path
    listener = unix_listener(path)
    observed = []

    def read_exact(conn, n):
        out=b""
        while len(out)<n:
            chunk=conn.recv(n-len(out))
            if not chunk: raise RuntimeError("closed")
            out+=chunk
        return out

    def read_client_text(conn):
        a,b=read_exact(conn,2); length=b & 0x7f
        assert b & 0x80
        if length==126: length=struct.unpack("!H",read_exact(conn,2))[0]
        elif length==127: length=struct.unpack("!Q",read_exact(conn,8))[0]
        mask=read_exact(conn,4); data=read_exact(conn,length)
        return bytes(x ^ mask[i%4] for i,x in enumerate(data)).decode()

    def send_text(conn, payload):
        data=json.dumps(payload,separators=(",",":")).encode()
        assert len(data)<126
        conn.sendall(bytes([0x81,len(data)])+data)

    def serve():
        conn,_=listener.accept()
        request=b""
        while b"\r\n\r\n" not in request: request+=conn.recv(4096)
        key=next(line.split(":",1)[1].strip() for line in request.decode().split("\r\n") if line.lower().startswith("sec-websocket-key:"))
        accept=base64.b64encode(hashlib.sha1((key+_GUID).encode()).digest()).decode()
        conn.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"+f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode())
        init=json.loads(read_client_text(conn)); observed.append(init)
        send_text(conn,{"id":init["id"],"result":{"userAgent":"codex_app_server/0.160.0"}})
        initialized=json.loads(read_client_text(conn)); observed.append(initialized)
        try: read_client_text(conn)  # best-effort close frame path may decode as non-text
        except Exception: pass
        conn.close()

    t=threading.Thread(target=serve); t.start()
    try:
        client=AppServerClient.connect(path,2)
        assert client.user_agent=="codex_app_server/0.160.0"
        client.close()
    finally:
        t.join(timeout=3); listener.close()
    assert observed[0]["method"]=="initialize"
    assert observed[0]["params"]["capabilities"]["experimentalApi"] is True
    assert observed[1]=={"method":"initialized"}
