"""
Science Tools - Các công cụ khoa học (Vật lý, Hóa học)
"""

import re


def register_science_tools(dispatcher):
    """Đăng ký các tool khoa học vào dispatcher"""
    
    def mcp_physics_calculation(query):
        from ..builtins import get as get_builtin
        # Extract physics calculation request
        
        # Check for different types of physics calculations
        if "định luật ohm" in query.lower() or "ohm" in query.lower():
            # Extract V, I, R values
            V_match = re.search(r'V[:\s=]+([\d.]+)', query, re.IGNORECASE)
            I_match = re.search(r'I[:\s=]+([\d.]+)', query, re.IGNORECASE) 
            R_match = re.search(r'R[:\s=]+([\d.]+)', query, re.IGNORECASE)
            
            args = {}
            if V_match: args["V"] = float(V_match.group(1))
            if I_match: args["I"] = float(I_match.group(1))
            if R_match: args["R"] = float(R_match.group(1))
            
            if len(args) >= 2:
                try:
                    spec = get_builtin("physics")
                    result = spec.call("ohms_law", args)
                    return f"Kết quả định luật Ohm: {result}"
                except Exception as e:
                    return f"Lỗi tính toán: {str(e)}"
        
        elif "vận tốc" in query.lower() or "kinematics" in query.lower():
            # Extract kinematics values
            u_match = re.search(r'u[:\s=]+([\d.]+)', query, re.IGNORECASE)
            a_match = re.search(r'a[:\s=]+([\d.]+)', query, re.IGNORECASE)
            t_match = re.search(r't[:\s=]+([\d.]+)', query, re.IGNORECASE)
            
            if u_match and a_match and t_match:
                try:
                    spec = get_builtin("physics")
                    result = spec.call("kinematics_v", {
                        "u": float(u_match.group(1)),
                        "a": float(a_match.group(1)),
                        "t": float(t_match.group(1))
                    })
                    return f"Kết quả chuyển động: {result}"
                except Exception as e:
                    return f"Lỗi tính toán: {str(e)}"
        
        elif "hằng số" in query.lower() or "constants" in query.lower():
            try:
                spec = get_builtin("physics")
                result = spec.call("constants", {})
                return f"Các hằng số vật lý: {result}"
            except Exception as e:
                return f"Lỗi lấy hằng số: {str(e)}"
        
        return "Tôi có thể giúp bạn tính toán vật lý. Ví dụ: 'tính V theo định luật Ohm với I=2A, R=10Ω'"

    def mcp_chemistry_calculation(query):
        from ..builtins import get as get_builtin
        query_lower = query.lower()
        
        if "khối lượng mol" in query_lower or "molar mass" in query_lower:
            # Extract chemical formula
            formula_match = re.search(r'([A-Z][a-z]?\d*)+', query)
            if formula_match:
                formula = formula_match.group(0)
                try:
                    spec = get_builtin("chemistry")
                    result = spec.call("molar_mass", {"formula": formula})
                    return f"Khối lượng mol của {formula}: {result}"
                except Exception as e:
                    return f"Lỗi tính toán: {str(e)}"
        
        elif "nguyên tố" in query_lower or "element" in query_lower:
            # Extract element symbol
            symbol_match = re.search(r'\b([A-Z][a-z]?)\b', query)
            if symbol_match:
                symbol = symbol_match.group(1)
                try:
                    spec = get_builtin("chemistry")
                    result = spec.call("lookup_element", {"symbol": symbol})
                    return f"Thông tin nguyên tố {symbol}: {result}"
                except Exception as e:
                    return f"Lỗi tra cứu: {str(e)}"
        
        elif "cân bằng" in query_lower or "balance" in query_lower:
            # Extract equation - look for chemical formulas with + and -> signs
            # Pattern to match equations like "h2 + o2" or "H2+O2->H2O"
            equation_patterns = [
                r'([A-Za-z0-9+\-\s>\=]+)',  # General chemical equation
                r'([A-Z][a-z]?\d*(?:\s*\+\s*[A-Z][a-z]?\d*)*(?:\s*->\s*[A-Z][a-z]?\d*)?)',  # Specific format
            ]
            
            equation = None
            for pattern in equation_patterns:
                equation_match = re.search(pattern, query, re.IGNORECASE)
                if equation_match:
                    potential_eq = equation_match.group(0).strip()
                    # Clean up the equation
                    if '+' in potential_eq or '->' in potential_eq or '=' in potential_eq:
                        equation = potential_eq
                        break
            
            # If no equation found in patterns, try to extract quoted text
            if not equation:
                quoted_match = re.search(r'["\']([^"\']+)["\']', query)
                if quoted_match:
                    equation = quoted_match.group(1).strip()
            
            if equation:
                try:
                    spec = get_builtin("chemistry")
                    result = spec.call("balance_equation", {"equation": equation})
                    balanced = result.get("balanced", equation)
                    return f"Cân bằng phương trình: {balanced}"
                except Exception as e:
                    return f"Lỗi cân bằng: {str(e)}"
            else:
                return "Không tìm thấy phương trình hóa học. Ví dụ: 'cân bằng H2 + O2 -> H2O'"
        
        return "Tôi có thể giúp bạn tính toán hóa học. Ví dụ: 'khối lượng mol của H2O' hoặc 'tra cứu nguyên tố Na'"

    # Đăng ký tools
    dispatcher.tools["physics_calculation"] = {
        "handler": mcp_physics_calculation,
        "description": "Tính toán các bài toán vật lý (định luật Ohm, chuyển động, lực, năng lượng).",
        "keywords": ["vật lý", "physics", "định luật ohm", "ohm", "vận tốc", "gia tốc", "lực", "năng lượng", "hằng số"]
    }

    dispatcher.tools["chemistry_calculation"] = {
        "handler": mcp_chemistry_calculation,
        "description": "Tính toán hóa học (khối lượng mol, tra cứu nguyên tố, cân bằng phương trình).",
        "keywords": ["hóa học", "chemistry", "khối lượng mol", "molar mass", "nguyên tố", "element", "cân bằng", "balance"]
    }
    
    print("Science tools registered successfully")
