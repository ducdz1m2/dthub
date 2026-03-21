import re
from fractions import Fraction
from typing import Any, Dict, List, Tuple

from .registry import BuiltinSpec, register


_ATOMIC_WEIGHTS: Dict[str, float] = {
    "H": 1.008, "He": 4.003,
    "Li": 6.941, "Be": 9.012, "B": 10.811, "C": 12.011,
    "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.180,
    "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.086,
    "P": 30.974, "S": 32.06, "Cl": 35.45, "Ar": 39.948,
    "K": 39.0983, "Ca": 40.078, "Fe": 55.845, "Cu": 63.546,
    "Zn": 65.38, "Ag": 107.868, "Au": 196.967, "Pb": 207.2,
    "Hg": 200.592, "Mn": 54.938, "Cr": 51.996, "Ni": 58.693,
    "Co": 58.933, "Ba": 137.327, "Br": 79.904, "I": 126.904,
}

_ELEMENTS: Dict[str, Dict[str, Any]] = {
    "H":  {"name": "Hydrogen",   "atomic_number": 1},
    "He": {"name": "Helium",     "atomic_number": 2},
    "Li": {"name": "Lithium",    "atomic_number": 3},
    "B":  {"name": "Boron",      "atomic_number": 5},
    "C":  {"name": "Carbon",     "atomic_number": 6},
    "N":  {"name": "Nitrogen",   "atomic_number": 7},
    "O":  {"name": "Oxygen",     "atomic_number": 8},
    "F":  {"name": "Fluorine",   "atomic_number": 9},
    "Na": {"name": "Sodium",     "atomic_number": 11},
    "Mg": {"name": "Magnesium",  "atomic_number": 12},
    "Al": {"name": "Aluminium",  "atomic_number": 13},
    "Si": {"name": "Silicon",    "atomic_number": 14},
    "P":  {"name": "Phosphorus", "atomic_number": 15},
    "S":  {"name": "Sulfur",     "atomic_number": 16},
    "Cl": {"name": "Chlorine",   "atomic_number": 17},
    "K":  {"name": "Potassium",  "atomic_number": 19},
    "Ca": {"name": "Calcium",    "atomic_number": 20},
    "Mn": {"name": "Manganese",  "atomic_number": 25},
    "Fe": {"name": "Iron",       "atomic_number": 26},
    "Co": {"name": "Cobalt",     "atomic_number": 27},
    "Ni": {"name": "Nickel",     "atomic_number": 28},
    "Cu": {"name": "Copper",     "atomic_number": 29},
    "Zn": {"name": "Zinc",       "atomic_number": 30},
    "Br": {"name": "Bromine",    "atomic_number": 35},
    "Ag": {"name": "Silver",     "atomic_number": 47},
    "I":  {"name": "Iodine",     "atomic_number": 53},
    "Ba": {"name": "Barium",     "atomic_number": 56},
    "Au": {"name": "Gold",       "atomic_number": 79},
    "Hg": {"name": "Mercury",    "atomic_number": 80},
    "Pb": {"name": "Lead",       "atomic_number": 82},
}


def _parse_formula(formula: str) -> Dict[str, int]:
    if not formula or not isinstance(formula, str):
        raise ValueError("formula is required")
    formula = formula.strip()
    # Xử lý ngoặc đơn: Ca(OH)2 → CaO2H2
    def _expand(f: str) -> str:
        while "(" in f:
            f = re.sub(r'\(([^()]+)\)(\d*)', lambda m: m.group(1) * (int(m.group(2)) if m.group(2) else 1), f)
        return f

    formula = _expand(formula)
    tokens: List[Tuple[str, str]] = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    if not tokens:
        raise ValueError("invalid formula")

    composition: Dict[str, int] = {}
    for symbol, count_str in tokens:
        if symbol not in _ATOMIC_WEIGHTS:
            raise ValueError(f"unsupported element: {symbol}")
        count = int(count_str) if count_str else 1
        composition[symbol] = composition.get(symbol, 0) + count

    return composition


def _balance_equation(equation: str) -> str:
    """Cân bằng phương trình hóa học bằng phương pháp đại số (null space).
    Hỗ trợ: H2 + O2 = H2O, Fe + O2 = Fe3O4, Ca(OH)2 + H2SO4 = CaSO4 + H2O
    """
    from fractions import Fraction
    from math import gcd
    from functools import reduce

    # Normalize
    eq = equation.strip().replace("→", "=").replace("->", "=")
    if "=" not in eq:
        raise ValueError("Phương trình phải có dấu '=' hoặc '→'")

    left_str, right_str = eq.split("=", 1)

    def _split(side):
        return [c.strip() for c in re.split(r'\s*\+\s*', side.strip()) if c.strip()]

    left_c = _split(left_str)
    right_c = _split(right_str)
    all_c = left_c + right_c
    n = len(all_c)
    n_left = len(left_c)

    if n < 2:
        raise ValueError("Phương trình không hợp lệ")

    parsed = [_parse_formula(c) for c in all_c]
    elements = sorted({el for comp in parsed for el in comp})
    m = len(elements)

    # Ma trận [m x n]: vế trái dương, vế phải âm
    A = []
    for el in elements:
        row = []
        for i, comp in enumerate(parsed):
            v = comp.get(el, 0)
            row.append(Fraction(v if i < n_left else -v))
        A.append(row)

    # Gaussian elimination → row echelon form
    mat = [row[:] for row in A]
    pivot_row = 0
    pivot_cols = []

    for col in range(n):
        # Tìm pivot trong cột này
        found = -1
        for r in range(pivot_row, m):
            if mat[r][col] != 0:
                found = r
                break
        if found == -1:
            continue
        mat[pivot_row], mat[found] = mat[found], mat[pivot_row]
        pv = mat[pivot_row][col]
        mat[pivot_row] = [x / pv for x in mat[pivot_row]]
        for r in range(m):
            if r != pivot_row and mat[r][col] != 0:
                f = mat[r][col]
                mat[r] = [mat[r][c] - f * mat[pivot_row][c] for c in range(n)]
        pivot_cols.append(col)
        pivot_row += 1

    free_cols = [c for c in range(n) if c not in pivot_cols]
    if not free_cols:
        # Không có free variable → kiểm tra xem [1,1,...,1] có thỏa mãn không
        ints = [1] * n
        ok = all(
            sum(parsed[i].get(el, 0) * ints[i] for i in range(n_left)) ==
            sum(parsed[n_left + i].get(el, 0) * ints[n_left + i] for i in range(len(right_c)))
            for el in elements
        )
        if ok:
            def _fmt0(compound, coeff):
                return compound if coeff == 1 else f"{coeff}{compound}"
            lp = [_fmt0(left_c[i], ints[i]) for i in range(n_left)]
            rp = [_fmt0(right_c[i], ints[n_left + i]) for i in range(len(right_c))]
            return " + ".join(lp) + " → " + " + ".join(rp)
        raise ValueError("Phương trình không thể cân bằng — có thể sản phẩm bị sai")

    # Đặt free variable cuối = 1, giải ngược
    free_col = free_cols[-1]
    solution = [Fraction(0)] * n
    solution[free_col] = Fraction(1)

    # Back-substitute: với mỗi pivot row, giải pivot variable
    for i, pc in enumerate(pivot_cols):
        if i >= m:
            break
        # mat[i][pc] = 1 (đã normalize), mat[i][free_col] = coeff
        solution[pc] = -mat[i][free_col]

    # Đảm bảo tất cả dương
    if any(s < 0 for s in solution):
        solution = [-s for s in solution]
    if any(s <= 0 for s in solution):
        raise ValueError("Không tìm được hệ số dương cho tất cả chất")

    # Quy về số nguyên
    denoms = [s.denominator for s in solution]
    lcm_val = reduce(lambda a, b: a * b // gcd(a, b), denoms)
    ints = [int(s * lcm_val) for s in solution]

    # Rút gọn
    g = reduce(gcd, ints)
    ints = [x // g for x in ints]

    # Kiểm tra
    for el in elements:
        lsum = sum(parsed[i].get(el, 0) * ints[i] for i in range(n_left))
        rsum = sum(parsed[n_left + i].get(el, 0) * ints[n_left + i] for i in range(len(right_c)))
        if lsum != rsum:
            raise ValueError(f"Cân bằng thất bại tại {el}: {lsum} ≠ {rsum}")

    def _fmt(compound, coeff):
        return compound if coeff == 1 else f"{coeff}{compound}"

    lparts = [_fmt(left_c[i], ints[i]) for i in range(n_left)]
    rparts = [_fmt(right_c[i], ints[n_left + i]) for i in range(len(right_c))]
    return " + ".join(lparts) + " → " + " + ".join(rparts)


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "lookup_element",
            "description": "Tra cứu nguyên tố hóa học: ký hiệu, số hiệu nguyên tử, nguyên tử khối.",
            "keywords": [
                "nguyên tố", "nguyên tử khối", "số hiệu nguyên tử", "ký hiệu hóa học",
                "atomic weight", "atomic number", "element", "bảng tuần hoàn",
                "khối lượng mol", "molar mass", "phân tử khối",
            ],
            "inputSchema": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"],
            },
        },
        {
            "name": "balance_equation",
            "description": "Cân bằng phương trình hóa học. Ví dụ: H2 + O2 = H2O",
            "keywords": [
                "cân bằng", "phương trình hóa học", "balance", "equation",
                "hóa học", "phản ứng", "hệ số",
            ],
            "inputSchema": {
                "type": "object",
                "properties": {"equation": {"type": "string"}},
                "required": ["equation"],
            },
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return []


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "lookup_element":
        symbol = (args.get("symbol") or "").strip()
        if not symbol:
            raise ValueError("symbol is required")
        element = _ELEMENTS.get(symbol)
        if not element:
            raise ValueError(f"unsupported element: {symbol}")
        return {
            "symbol": symbol,
            "name": element["name"],
            "atomic_number": element["atomic_number"],
            "atomic_weight": _ATOMIC_WEIGHTS.get(symbol),
        }

    if tool_name == "balance_equation":
        equation = (args.get("equation") or "").strip()
        if not equation:
            raise ValueError("equation is required")
        try:
            balanced = _balance_equation(equation)
            return {"input": equation, "balanced": balanced}
        except Exception as e:
            return {"input": equation, "balanced": equation, "error": str(e)}

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="chemistry",
        label="MCP tích hợp: Hóa học",
        name="chemistry-mcp (builtin)",
        version="0.2",
        description="Tra cứu nguyên tố và cân bằng phương trình hóa học.",
        tools=tools,
        resources=resources,
        call=call,
    )
)

