#!/usr/bin/env python3
import datetime
import http.client
import http.server
import json
import os
import itertools
import sys
import threading
import urllib.parse


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def usage() -> None:
    script = os.path.basename(sys.argv[0])
    print(f"Usage: {script} [log-file]")
    print(f"Example: {script} my-session.log")
    print("Environment variables:")
    print("  LISTEN_HOST (default: 127.0.0.1)")
    print("  LISTEN_PORT (default: 11435)")
    print("  UPSTREAM    (default: http://127.0.0.1:11434)")


def pretty_body(body_bytes: bytes, limit: int = 500000) -> str:
    if not body_bytes:
        return ""
    text = body_bytes.decode("utf-8", errors="replace")
    if len(text) > limit:
        text = text[:limit] + "\n...truncated..."

    # Try plain JSON first.
    try:
        obj = json.loads(text)
        return json.dumps(obj, ensure_ascii=True, indent=2)
    except Exception:
        pass

    # Try NDJSON (streaming responses).
    lines = [line for line in text.splitlines() if line.strip()]
    if lines:
        parsed = []
        all_json = True
        for line in lines:
            try:
                parsed.append(json.loads(line))
            except Exception:
                all_json = False
                break
        if all_json:
            return json.dumps(parsed, ensure_ascii=True, indent=2)

    return text


def try_parse_json_or_ndjson(body_bytes: bytes):
    if not body_bytes:
        return None

    text = body_bytes.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except Exception:
        pass

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    items = []
    for line in lines:
        try:
            items.append(json.loads(line))
        except Exception:
            return None
    return items


def extract_prompt(path: str, req_json) -> str:
    if req_json is None:
        return ""

    data = req_json[0] if isinstance(req_json, list) and req_json else req_json
    if not isinstance(data, dict):
        return ""

    if path.startswith("/api/generate"):
        return str(data.get("prompt", ""))

    if path.startswith("/api/chat"):
        messages = data.get("messages", [])
        if isinstance(messages, list):
            for item in reversed(messages):
                if isinstance(item, dict) and item.get("role") == "user":
                    return str(item.get("content", ""))
        return ""

    if path.startswith("/v1/chat/completions"):
        messages = data.get("messages", [])
        if isinstance(messages, list):
            for item in reversed(messages):
                if isinstance(item, dict) and item.get("role") == "user":
                    return str(item.get("content", ""))
        return ""

    if path.startswith("/v1/completions"):
        return str(data.get("prompt", ""))

    return ""


def extract_assistant_and_metrics(path: str, resp_json):
    assistant_text = ""
    metrics = {}

    if resp_json is None:
        return assistant_text, metrics

    # Handle NDJSON streaming payloads captured as a list.
    if isinstance(resp_json, list):
        chunks = []
        tail = {}
        for item in resp_json:
            if not isinstance(item, dict):
                continue
            if path.startswith("/api/chat"):
                msg = item.get("message", {})
                piece = msg.get("content", "") if isinstance(msg, dict) else ""
                if piece:
                    chunks.append(str(piece))
            elif path.startswith("/api/generate"):
                piece = item.get("response", "")
                if piece:
                    chunks.append(str(piece))
            tail = item
        assistant_text = "".join(chunks)
        if isinstance(tail, dict):
            for key in ["total_duration", "eval_count", "prompt_eval_count"]:
                if key in tail:
                    metrics[key] = tail[key]
        return assistant_text, metrics

    if not isinstance(resp_json, dict):
        return assistant_text, metrics

    if path.startswith("/api/chat"):
        msg = resp_json.get("message", {})
        if isinstance(msg, dict):
            assistant_text = str(msg.get("content", ""))
    elif path.startswith("/api/generate"):
        assistant_text = str(resp_json.get("response", ""))
    elif path.startswith("/v1/chat/completions"):
        choices = resp_json.get("choices", [])
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    assistant_text = str(message.get("content", ""))
    elif path.startswith("/v1/completions"):
        choices = resp_json.get("choices", [])
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                assistant_text = str(first.get("text", ""))

    for key in ["total_duration", "eval_count", "prompt_eval_count"]:
        if key in resp_json:
            metrics[key] = resp_json[key]

    return assistant_text, metrics


class Logger:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.lock = threading.Lock()

    def write(self, line: str) -> None:
        full = f"[{now()}] {line}"
        with self.lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(full + "\n")
        print(full, flush=True)


def build_proxy_handler(upstream: urllib.parse.SplitResult, logger: Logger):
    request_counter = itertools.count(1)

    class Proxy(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _handle(self) -> None:
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            req_body = self.rfile.read(content_length) if content_length > 0 else b""

            raw_path = self.path if self.path.startswith("/") else "/" + self.path
            forward_path = (upstream.path.rstrip("/") + raw_path) if upstream.path else raw_path

            headers = {k: v for k, v in self.headers.items()}
            headers["Host"] = f"{upstream.hostname}:{upstream.port or 80}"
            for hop in ["Connection", "Proxy-Connection", "Keep-Alive", "Transfer-Encoding", "Upgrade"]:
                headers.pop(hop, None)

            should_log = raw_path.startswith("/api/") or raw_path.startswith("/v1/")
            request_id = next(request_counter)
            if should_log:
                logger.write("=" * 72)
                logger.write(f"REQUEST #{request_id} {self.command} {raw_path}")
                if req_body:
                    logger.write("REQUEST BODY:")
                    for line in pretty_body(req_body).splitlines():
                        logger.write("  " + line)

            conn = http.client.HTTPConnection(upstream.hostname, upstream.port or 80, timeout=600)
            conn.request(self.command, forward_path, body=req_body if content_length > 0 else None, headers=headers)
            resp = conn.getresponse()
            resp_body = resp.read()

            self.send_response(resp.status, resp.reason)
            hop_by_hop = {
                "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
                "te", "trailers", "transfer-encoding", "upgrade"
            }
            for key, value in resp.getheaders():
                if key.lower() in hop_by_hop:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            if resp_body:
                self.wfile.write(resp_body)
            self.wfile.flush()
            conn.close()

            if should_log:
                logger.write(f"RESPONSE #{request_id} {resp.status} {raw_path}")
                if resp_body:
                    logger.write("RESPONSE BODY:")
                    for line in pretty_body(resp_body).splitlines():
                        logger.write("  " + line)

                req_json = try_parse_json_or_ndjson(req_body)
                resp_json = try_parse_json_or_ndjson(resp_body)
                prompt = extract_prompt(raw_path, req_json)
                assistant_text, raw_metrics = extract_assistant_and_metrics(raw_path, resp_json)

                if prompt or assistant_text:
                    total_duration_ms = None
                    if "total_duration" in raw_metrics:
                        try:
                            total_duration_ms = round(float(raw_metrics["total_duration"]) / 1_000_000)
                        except Exception:
                            total_duration_ms = None

                    metrics = {
                        "total_duration_ms": total_duration_ms if total_duration_ms is not None else 0,
                        "eval_count": raw_metrics.get("eval_count", 0),
                        "prompt_eval_count": raw_metrics.get("prompt_eval_count", 0),
                    }

                    logger.write("-" * 72)
                    logger.write(f"Timestamp: {now()}")
                    logger.write(f"Path: {raw_path}")
                    logger.write(f"User: {prompt}")
                    logger.write("Assistant:")
                    if assistant_text:
                        for line in assistant_text.splitlines():
                            logger.write(line)
                    else:
                        logger.write("(empty)")
                    logger.write("Metrics:")
                    logger.write(json.dumps(metrics, ensure_ascii=True))

        def do_GET(self):
            self._handle()

        def do_POST(self):
            self._handle()

        def do_PUT(self):
            self._handle()

        def do_PATCH(self):
            self._handle()

        def do_DELETE(self):
            self._handle()

        def log_message(self, fmt, *args):
            return

    return Proxy


def main() -> int:
    if len(sys.argv) > 2:
        usage()
        return 1

    log_file = sys.argv[1] if len(sys.argv) == 2 else f"ollama-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    listen_host = os.environ.get("LISTEN_HOST", "127.0.0.1")
    listen_port = int(os.environ.get("LISTEN_PORT", "11435"))
    upstream_url = os.environ.get("UPSTREAM", "http://127.0.0.1:11434")

    upstream = urllib.parse.urlsplit(upstream_url)
    if upstream.scheme != "http" or not upstream.hostname:
        print("ERROR: UPSTREAM must be http://host:port")
        return 1

    logger = Logger(log_file)

    print("Starting Ollama proxy logger")
    print(f"Log file: {log_file}")
    print(f"Listening on: http://{listen_host}:{listen_port}")
    print(f"Upstream: {upstream_url}")
    print("Point your clients (Copilot/Ollama clients) to the listening URL above.")
    print("Stopping this logger does NOT stop Ollama or loaded models.")
    print("Press Ctrl+C to stop.")

    logger.write("=== OLLAMA PROXY LOGGER STARTED ===")
    logger.write(f"LISTEN {listen_host}:{listen_port}")
    logger.write(f"UPSTREAM {upstream_url}")

    handler = build_proxy_handler(upstream, logger)
    server = http.server.ThreadingHTTPServer((listen_host, listen_port), handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        logger.write("=== OLLAMA PROXY LOGGER STOPPED ===")
        logger.write("UPSTREAM OLLAMA/MODELS LEFT RUNNING")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
