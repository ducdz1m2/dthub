import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    body = handler.rfile.read(length).decode("utf-8")
    if not body:
        return {}
    return json.loads(body)


PHYS_CONSTANTS = {
    "g": 9.81,
    "c": 299_792_458,
    "R": 8.314462618,
}


class PhysicsMCPHandler(BaseHTTPRequestHandler):
    server_version = "PhysicsMCP/0.1"

    def do_GET(self):
        if self.path == "/info":
            return json_response(self, 200, {"name": "physics-mcp", "status": "ok"})

        if self.path == "/mcp/info":
            return json_response(
                self,
                200,
                {
                    "name": "physics-mcp",
                    "version": "0.1",
                    "description": "MCP server for basic physics utilities (demo).",
                },
            )

        if self.path == "/mcp/tools":
            return json_response(
                self,
                200,
                {
                    "tools": [
                        {
                            "name": "ohms_law",
                            "description": "Compute missing V/I/R using Ohm's law (V=I*R). Provide any 2.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "V": {"type": "number"},
                                    "I": {"type": "number"},
                                    "R": {"type": "number"},
                                },
                            },
                        },
                        {
                            "name": "kinematics_v",
                            "description": "Compute v = u + a*t.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "u": {"type": "number"},
                                    "a": {"type": "number"},
                                    "t": {"type": "number"},
                                },
                                "required": ["u", "a", "t"],
                            },
                        },
                        {
                            "name": "constants",
                            "description": "Return a small set of physics constants.",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                    ]
                },
            )

        if self.path == "/mcp/resources":
            return json_response(
                self,
                200,
                {
                    "resources": [
                        {
                            "uri": "physics://constants",
                            "name": "Physics constants",
                            "description": "Small set of constants (g, c, R).",
                            "mimeType": "application/json",
                        },
                        {
                            "uri": "physics://formula_sheet/basic",
                            "name": "Basic formula sheet",
                            "description": "Common formulas for quick reference.",
                            "mimeType": "text/plain",
                        },
                    ]
                },
            )

        return json_response(self, 404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/mcp/call":
            return json_response(self, 404, {"error": "not found"})

        try:
            payload = read_json(self)
            tool_name = payload.get("name")
            arguments = payload.get("arguments") or {}

            if tool_name == "ohms_law":
                V = arguments.get("V")
                I = arguments.get("I")
                R = arguments.get("R")

                provided = [x is not None for x in (V, I, R)].count(True)
                if provided < 2:
                    return json_response(self, 400, {"error": "Provide at least two of V, I, R"})

                if V is None:
                    result = {"V": I * R, "I": I, "R": R}
                elif I is None:
                    result = {"V": V, "I": V / R, "R": R}
                else:
                    result = {"V": V, "I": I, "R": V / I}

                return json_response(self, 200, {"success": True, "result": result})

            if tool_name == "kinematics_v":
                u = arguments.get("u")
                a = arguments.get("a")
                t = arguments.get("t")
                if u is None or a is None or t is None:
                    return json_response(self, 400, {"error": "u, a, t are required"})
                return json_response(self, 200, {"success": True, "result": {"v": u + a * t}})

            if tool_name == "constants":
                return json_response(self, 200, {"success": True, "result": PHYS_CONSTANTS})

            return json_response(self, 400, {"error": f"unknown tool: {tool_name}"})
        except Exception as e:
            return json_response(self, 500, {"error": str(e)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9102)
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), PhysicsMCPHandler)
    print(f"Physics MCP server running at http://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

