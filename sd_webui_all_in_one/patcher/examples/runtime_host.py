"""运行时 TCP JSONL 最小宿主示例"""

from __future__ import annotations

import json
import socketserver


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        hello = json.loads(self.rfile.readline().decode("utf-8"))
        print("hello:", hello)

        if hello.get("type") == "channel.open":
            print("raw channel:", hello.get("channel"))
            return

        for raw_line in self.rfile:
            message = json.loads(raw_line.decode("utf-8"))
            if str(message.get("type", "")).startswith("log."):
                print("log:", message["type"], message.get("payload", {}))
            else:
                print("message:", message)

            message_id = message.get("id")
            if message_id is None:
                continue

            if message.get("type") == "config.get":
                payload = {"config": {"from_host": True, "answer": 42}}
            else:
                payload = {"accepted": True}

            response = {"id": message_id, "ok": True, "payload": payload}
            self.wfile.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
            self.wfile.flush()


def main():
    """启动 runtime host 示例服务"""

    with socketserver.ThreadingTCPServer(("127.0.0.1", 8765), Handler) as server:
        print("sd_webui_all_in_one_hotpatcher runtime host listening on 127.0.0.1:8765")
        server.serve_forever()


if __name__ == "__main__":
    main()
