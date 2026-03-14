import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ATOMIC_WEIGHTS = {
    "H": 1.008,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "Na": 22.990,
    "Cl": 35.45,
    "S": 32.06,
    "K": 39.0983,
    "Ca": 40.078,
    "Fe": 55.845,
}

ELEMENTS = {
    "H": {"name": "Hydrogen", "atomic_number": 1},
    "C": {"name": "Carbon", "atomic_number": 6},
    "N": {"name": "Nitrogen", "atomic_number": 7},
    "O": {"name": "Oxygen", "atomic_number": 8},
    "Na": {"name": "Sodium", "atomic_number": 11},
    "Cl": {"name": "Chlorine", "atomic_number": 17},
    "S": {"name": "Sulfur", "atomic_number": 16},
    "K": {"name": "Potassium", "atomic_number": 19},
    "Ca": {"name": "Calcium", "atomic_number": 20},
    "Fe": {"name": "Iron", "atomic_number": 26},
}


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


def parse_formula(formula: str) -> dict:
    if not formula or not isinstance(formula, str):
        raise ValueError("formula is required")
    formula = formula.strip()
    if not formula:
        raise ValueError("formula is required")

    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    if not tokens:
        raise ValueError("invalid formula")

    composition = {}
    for symbol, count_str in tokens:
        if symbol not in ATOMIC_WEIGHTS:
            raise ValueError(f"unsupported element: {symbol}")
        count = int(count_str) if count_str else 1
        composition[symbol] = composition.get(symbol, 0) + count

    return composition


def molar_mass(formula: str) -> dict:
    composition = parse_formula(formula)
    mass = 0.0
    for symbol, count in composition.items():
        mass += ATOMIC_WEIGHTS[symbol] * count
    return {"formula": formula, "molar_mass": round(mass, 4), "composition": composition}


class ChemistryMCPHandler(BaseHTTPRequestHandler):
    server_version = "ChemistryMCP/0.1"

    def do_GET(self):
        if self.path == "/info":
            return json_response(self, 200, {"name": "chemistry-mcp", "status": "ok"})

        if self.path == "/mcp/info":
            return json_response(
                self,
                200,
                {
                    "name": "chemistry-mcp",
                    "version": "0.1",
                    "description": "MCP server for basic chemistry utilities (demo).",
                },
            )

        if self.path == "/mcp/tools":
            return json_response(
                self,
                200,
                {
                    "tools": [
                        {
                            "name": "lookup_element",
                            "description": "Lookup basic data for an element by symbol (H, O, Na...).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"symbol": {"type": "string"}},
                                "required": ["symbol"],
                            },
                        },
                        {
                            "name": "molar_mass",
                            "description": "Compute molar mass for a simple chemical formula (no parentheses).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"formula": {"type": "string"}},
                                "required": ["formula"],
                            },
                        },
                        {
                            "name": "balance_equation",
                            "description": "Balance a chemical equation (demo stub).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"equation": {"type": "string"}},
                                "required": ["equation"],
                            },
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
                            "uri": "chem://constants/atomic_weights",
                            "name": "Atomic Weights (subset)",
                            "description": "Atomic weights used by the demo molar_mass tool.",
                            "mimeType": "application/json",
                        },
                        {
                            "uri": "chem://notes/balancing",
                            "name": "Balancing Notes",
                            "description": "Short notes on balancing chemical equations.",
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

            if tool_name == "lookup_element":
                symbol = (arguments.get("symbol") or "").strip()
                if not symbol:
                    return json_response(self, 400, {"error": "symbol is required"})
                element = ELEMENTS.get(symbol)
                if not element:
                    return json_response(self, 400, {"error": f"unsupported element: {symbol}"})
                result = {
                    "symbol": symbol,
                    "name": element["name"],
                    "atomic_number": element["atomic_number"],
                    "atomic_weight": ATOMIC_WEIGHTS.get(symbol),
                }
                return json_response(self, 200, {"success": True, "result": result})

            if tool_name == "molar_mass":
                formula = (arguments.get("formula") or "").strip()
                result = molar_mass(formula)
                return json_response(self, 200, {"success": True, "result": result})

            if tool_name == "balance_equation":
                equation = (arguments.get("equation") or "").strip()
                if not equation:
                    return json_response(self, 400, {"error": "equation is required"})
                return json_response(
                    self,
                    200,
                    {"success": True, "result": {"input": equation, "balanced": equation, "note": "demo stub"}},
                )

            return json_response(self, 400, {"error": f"unknown tool: {tool_name}"})
        except Exception as e:
            return json_response(self, 500, {"error": str(e)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9101)
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), ChemistryMCPHandler)
    print(f"Chemistry MCP server running at http://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

