"""
rag_builtin_handlers.py — Smart param parsing cho builtin tools.
"""

import re


def _call_builtin(spec_call, tool_name: str, query: str, schema: dict):
    """Gọi builtin tool với smart param parsing từ query string."""
    required = schema.get("required", [])
    props = schema.get("properties", {})

    if "title" in props:
        title = re.sub(
            r'^(?:tóm\s*tắt\s+(?:bài\s+)?(?:wikipedia\s+)?(?:về\s+)?|'
            r'tóm\s*lược\s+(?:bài\s+)?(?:wikipedia\s+)?(?:về\s+)?|'
            r'wikipedia\s+(?:về\s+)?|wiki\s+(?:về\s+)?|'
            r'summary\s+(?:of\s+)?(?:wikipedia\s+)?(?:about\s+)?)',
            '', query, flags=re.IGNORECASE
        ).strip()
        quoted = re.findall(r'["\']([^"\']+)["\']', title)
        args = {"title": quoted[0] if quoted else title}

    elif "expression" in props:
        expr = re.sub(r'^(tính|calculate|calc|compute|tính toán)\s+', '', query, flags=re.IGNORECASE).strip()
        args = {"expression": expr}

    elif "equation" in props:
        eq = re.sub(r'^(thử\s+)?(cân\s+bằng\s+)?(phương\s+trình\s+)?', '', query, flags=re.IGNORECASE).strip()
        eq = eq.replace("→", "=").replace("->", "=")
        args = {"equation": eq}

    elif "formula" in props:
        formula = re.search(r'[A-Z][a-zA-Z0-9()]*', query)
        args = {"formula": formula.group(0) if formula else query}

    elif "symbol" in props:
        _VI_TO_SYMBOL = {
            "hydro": "H", "hydrogen": "H", "heli": "He", "helium": "He",
            "liti": "Li", "lithium": "Li", "carbon": "C", "cacbon": "C",
            "nito": "N", "nitơ": "N", "nitrogen": "N",
            "oxy": "O", "oxi": "O", "oxygen": "O",
            "natri": "Na", "sodium": "Na", "magie": "Mg", "magnesium": "Mg",
            "nhôm": "Al", "nhom": "Al", "aluminium": "Al", "aluminum": "Al",
            "silic": "Si", "silicon": "Si", "photpho": "P", "phosphorus": "P",
            "lưu huỳnh": "S", "luu huynh": "S", "sulfur": "S",
            "clo": "Cl", "chlorine": "Cl", "kali": "K", "potassium": "K",
            "canxi": "Ca", "calcium": "Ca", "sắt": "Fe", "sat": "Fe", "iron": "Fe",
            "đồng": "Cu", "dong": "Cu", "copper": "Cu",
            "kẽm": "Zn", "kem": "Zn", "zinc": "Zn",
            "bạc": "Ag", "bac": "Ag", "silver": "Ag",
            "vàng": "Au", "vang": "Au", "gold": "Au",
            "chì": "Pb", "chi": "Pb", "lead": "Pb",
            "thủy ngân": "Hg", "thuy ngan": "Hg", "mercury": "Hg",
        }
        q_lower = query.lower()
        symbol = next((sym for name_key, sym in _VI_TO_SYMBOL.items() if name_key in q_lower), None)
        if not symbol:
            m = re.search(r'\b([A-Z][a-z]?)\b', query)
            symbol = m.group(1) if m else query.strip()
        args = {"symbol": symbol}

    elif "V" in props or "I" in props or "R" in props:
        def _num(pattern):
            m = re.search(pattern, query, re.IGNORECASE)
            return float(m.group(1)) if m else None
        args = {k: v for k, v in {
            "V": _num(r'\bV\s*=\s*([\d.]+)'),
            "I": _num(r'\bI\s*=\s*([\d.]+)'),
            "R": _num(r'\bR\s*=\s*([\d.]+)'),
        }.items() if v is not None}

    elif "u" in props and "a" in props and "t" in props:
        def _num(pattern):
            m = re.search(pattern, query, re.IGNORECASE)
            return float(m.group(1)) if m else None
        u = _num(r'\b(?:u|v0|v_0)\s*=\s*(-?[\d.]+)')
        a = _num(r'\ba\s*=\s*(-?[\d.]+)')
        t = _num(r'\bt\s*=\s*(-?[\d.]+)') or _num(r'(?:sau|trong|after)\s+(-?[\d.]+)\s*s')
        if u is None and a is None and t is None:
            nums = re.findall(r'-?[\d.]+', query)
            if len(nums) >= 3:
                u, a, t = float(nums[0]), float(nums[1]), float(nums[2])
            elif len(nums) == 2:
                u, a, t = 0.0, float(nums[0]), float(nums[1])
        args = {"u": u or 0.0, "a": a or 0.0, "t": t or 0.0}

    elif "a" in props and "b" in props and "c" in props:
        def _extract_abc(q):
            ma = re.search(r'\ba\s*=\s*(-?[\d.]+)', q, re.IGNORECASE)
            mb = re.search(r'\bb\s*=\s*(-?[\d.]+)', q, re.IGNORECASE)
            mc = re.search(r'\bc\s*=\s*(-?[\d.]+)', q, re.IGNORECASE)
            if ma and mb and mc:
                return float(ma.group(1)), float(mb.group(1)), float(mc.group(1))
            norm = q.replace('²', '^2').replace('x^2', 'X2').replace('x', 'X')
            m = re.search(
                r'(-?[\d.]*)\s*X2\s*([+-]?\s*[\d.]*)\s*X\s*([+-]?\s*[\d.]+)\s*=\s*0',
                norm, re.IGNORECASE
            )
            if m:
                def _coef(s, default):
                    s = s.replace(' ', '') or default
                    return '-1' if s == '-' else ('1' if s in ('', '+') else s)
                return float(_coef(m.group(1), '1')), float(_coef(m.group(2), '0')), float(m.group(3).replace(' ', ''))
            nums = re.findall(r'-?[\d.]+', q)
            if len(nums) >= 3:
                return float(nums[0]), float(nums[1]), float(nums[2])
            return None, None, None

        a_val, b_val, c_val = _extract_abc(query)
        if a_val is None:
            return f"Lỗi thực thi {tool_name}: Không thể trích hệ số a, b, c từ '{query}'"
        args = {"a": a_val, "b": b_val, "c": c_val}

    elif len(required) == 1:
        key = required[0]
        if key == "query":
            cleaned = re.sub(
                r'^(tìm\s+(?:kiếm\s+)?(?:thông\s+tin\s+(?:về\s+)?)?|'
                r'search\s+(?:for\s+)?|tra\s+cứu\s+(?:về\s+)?|'
                r'hỏi\s+về\s+|thông\s+tin\s+về\s+|cho\s+tôi\s+biết\s+về\s+|'
                r'giới\s+thiệu\s+về\s+)',
                '', query, flags=re.IGNORECASE
            ).strip()
            cleaned = re.sub(
                r'\s+(là\s+ai|là\s+gì|là\s+người\s+(?:như\s+thế\s+nào|thế\s+nào)?|'
                r'như\s+thế\s+nào|ra\s+sao|có\s+phải|không\??|là\s+gì\??)$',
                '', cleaned, flags=re.IGNORECASE
            ).strip()
            quoted = re.findall(r'["\']([^"\']+)["\']', cleaned)
            args = {key: quoted[0] if quoted else cleaned}
        else:
            args = {key: query}

    else:
        args = {"query": query}

    try:
        result = spec_call(tool_name, args)
        return result if isinstance(result, dict) else str(result)
    except Exception as e:
        return f"Lỗi thực thi {tool_name}: {e}"
