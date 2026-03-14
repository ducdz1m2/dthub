"""
Dictionary Tools - Các công cụ tra cứu từ điển (Anh, Nhật)
"""

import re


def register_dictionary_tools(dispatcher):
    """Đăng ký các tool tra cứu từ điển vào dispatcher"""
    
    def _extract_quoted(text: str) -> str:
        import re
        m = re.search(r'["\'"'"'"'](.+?)["\'"'"'"']', text)
        if m:
            return (m.group(1) or "").strip()
        return ""

    def mcp_english_define(query):
        from ..builtins import get as get_builtin
        
        # Nếu query là dict (từ Orchestrator mới), lấy 'word'
        if isinstance(query, dict):
            word = query.get('word', query.get('query', ''))
        else:
            word = _extract_quoted(query)
            if not word:
                q = query.strip()
                for prefix in ["từ", "word"]:
                    if q.lower().startswith(prefix):
                        q = q[len(prefix):].strip()
                word = q.split()[0] if q else ""
        
        word = (word or "").strip(".,;:!?()[]{}").strip()
        if not word:
            return "Bạn muốn tra nghĩa từ nào? Ví dụ: từ 'laugh' nghĩa là gì trong tiếng Anh?"
            
        try:
            spec = get_builtin("english")
            data = spec.call("english_define", {"word": word})
            if not data.get("found"):
                return f"Không tìm thấy từ '{word}' trong từ điển tiếng Anh."
            
            entries = data.get("entries") or []
            output = f"DỮ LIỆU TỪ ĐIỂN ANH-VIỆT CHO '{word}':\n"
            if entries and entries[0].get("phonetic"):
                output += f"- Phiên âm: {entries[0].get('phonetic')}\n"
                
            for entry in entries[:1]:
                for meaning in (entry.get("meanings") or [])[:2]:
                    part = meaning.get("partOfSpeech") or ""
                    defs = meaning.get("definitions") or []
                    if part:
                        output += f"- {part}:\n"
                    for d in defs[:2]:
                        definition = (d.get("definition") or "").strip()
                        example = (d.get("example") or "").strip()
                        if definition:
                            output += f"  + Nghĩa: {definition}\n"
                        if example:
                            output += f"    Ví dụ: {example}\n"
            return output.strip()
        except Exception as e:
            return f"Lỗi tra cứu tiếng Anh: {str(e)}"

    def mcp_japanese_lookup(query):
        from ..builtins import get as get_builtin
        
        # Nếu query là dict (từ Orchestrator mới), lấy 'keyword' hoặc 'word'
        if isinstance(query, dict):
            keyword = query.get('keyword', query.get('word', query.get('query', '')))
        else:
            # Extract Japanese characters or quoted text
            keyword = _extract_quoted(query)
            
            # Try to extract Japanese characters if no quoted text
            if not keyword:
                # Look for Japanese characters in the query
                japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+'
                matches = re.findall(japanese_pattern, query)
                if matches:
                    keyword = matches[0]
                else:
                    # Try ord() based detection as fallback
                    for char in query:
                        if (0x3040 <= ord(char) <= 0x309F or  # Hiragana
                            0x30A0 <= ord(char) <= 0x30FF or  # Katakana  
                            0x4E00 <= ord(char) <= 0x9FAF):   # Kanji
                            keyword = char
                            break
            
            if not keyword:
                keyword = query.strip()
        
        keyword = (keyword or "").strip()
        if not keyword:
            return "Bạn muốn tra từ/kanji nào? Ví dụ: '勉強' nghĩa là gì?"

        # VN disambiguation
        if keyword.lower() in ["đức", "duc"]:
            return "\n".join(
                [
                    """"Đức" trong tiếng Việt có thể hiểu theo 2 nghĩa phổ biến, tiếng Nhật tương ứng là:""",
                    "- Quốc gia Đức (Germany): ドイツ (doitsu)",
                    "- Đức hạnh / đạo đức (virtue, morality): 徳 (とく, toku) / 道徳 (どうとく, dōtoku)",
                    "Bạn đang hỏi theo nghĩa nào để mình giải thích chi tiết hơn?",
                ]
            )
        
        try:
            spec = get_builtin("japanese")
            data = spec.call("japanese_lookup", {"keyword": keyword})
            results = data.get("results") or []
            if not results:
                return f"Không tìm thấy kết quả nào cho từ '{keyword}' trong từ điển tiếng Nhật."
            
            first = results[0]
            word_found = first.get("word") or keyword
            reading = first.get("reading") or ""
            
            # Format results for LLM
            output = f"DỮ LIỆU TỪ ĐIỂN NHẬT-VIỆT CHO '{keyword}':\n"
            output += f"- Từ/Kanji: {word_found}\n"
            if reading:
                output += f"- Cách đọc: {reading}\n"
            
            senses = first.get("senses") or []
            if senses:
                output += "- Nghĩa (English): " + ", ".join(senses[0].get("english_definitions", []))
                if len(senses) > 1:
                    output += "\n- Nghĩa khác: " + ", ".join(senses[1].get("english_definitions", []))
            
            output += "\n\nQUY TẮC: Hãy dịch các nghĩa tiếng Anh trên sang tiếng Việt một cách chính xác nhất."
            return output
        except Exception as e:
            return f"Lỗi hệ thống khi tra cứu tiếng Nhật: {str(e)}"

    # Register tools
    dispatcher.tools["english_define"] = {
        "handler": mcp_english_define,
        "description": "Tra cứu nghĩa của một từ tiếng Anh (Oxford Dictionary)",
        "keywords": ["tiếng anh", "english", "meaning", "define", "nghĩa là gì", "từ", "word", "dịch"],
        "display_name": "Từ điển Anh-Việt"
    }
    
    dispatcher.tools["japanese_lookup"] = {
        "handler": mcp_japanese_lookup,
        "description": "Tra cứu nghĩa từ vựng, Kanji tiếng Nhật (Jisho API)",
        "keywords": ["tiếng nhật", "japanese", "kanji", "hiragana", "katakana", "nihongo", "nghĩa là gì", "dịch"],
        "display_name": "Từ điển Nhật-Việt"
    }
    
    print("Dictionary tools registered successfully")
