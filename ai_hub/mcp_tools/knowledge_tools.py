"""
Knowledge Tools - Các công cụ tra cứu kiến thức (Wikipedia, RAG)
"""

import re


def register_knowledge_tools(dispatcher, retriever=None):
    """Đăng ký các tool tra cứu kiến thức vào dispatcher
    
    Args:
        dispatcher: MCP dispatcher
        retriever: Vector database retriever cho RAG search (optional)
    """
    
    def mcp_wiki_search(query):
        from ..builtins import get as get_builtin
        # Extract search query from user input
        # Try to extract quoted text first
        quoted_match = re.search(r'["""](.+?)["""]', query)
        if quoted_match:
            search_term = quoted_match.group(1).strip()
        else:
            # Remove common prefixes and use the rest
            search_term = query.lower()
            for prefix in ["tìm kiếm", "tìm", "search", "wiki", "wikipedia", "tra cứu"]:
                if search_term.startswith(prefix):
                    search_term = search_term[len(prefix):].strip()
                    break
            # Remove question words
            for qword in ["về", "là gì", "what is", "what are"]:
                if qword in search_term:
                    search_term = search_term.replace(qword, "").strip()
                    break
            search_term = search_term.strip(" ?!.,;")
        
        if not search_term:
            return "Bạn muốn tìm kiếm thông tin về gì? Ví dụ: 'tìm Albert Einstein' hoặc 'wikipedia Python'"
        
        try:
            spec = get_builtin("knowledge")
            result = spec.call("wiki_search", {"query": search_term, "lang": "vi", "limit": 5})
            results = result.get("results", [])
            if not results:
                return f"Không tìm thấy kết quả cho '{search_term}' trên Wikipedia."
            
            response = f"Tìm thấy {len(results)} kết quả cho '{search_term}':\n\n"
            for i, item in enumerate(results[:3], 1):
                title = item.get("title", "")
                url = item.get("url", "")
                response += f"{i}. {title}\n   {url}\n\n"
            
            if len(results) > 3:
                response += f"... và {len(results) - 3} kết quả khác."
            
            return response
        except Exception as e:
            return f"Lỗi khi tìm kiếm Wikipedia: {str(e)}"

    def mcp_wiki_summary(query):
        from ..builtins import get as get_builtin
        # Extract page title from user input
        quoted_match = re.search(r'["""](.+?)["""]', query)
        if quoted_match:
            title = quoted_match.group(1).strip()
        else:
            # Remove common prefixes
            title = query.lower()
            for prefix in ["tóm tắt", "summary", "wiki", "wikipedia", "thông tin"]:
                if title.startswith(prefix):
                    title = title[len(prefix):].strip()
                    break
            title = title.strip(" ?!.,;")
        
        if not title:
            return "Bạn muốn xem tóm tắt về gì? Ví dụ: 'tóm tắt Albert Einstein' hoặc 'wikipedia Python'"
        
        try:
            spec = get_builtin("knowledge")
            result = spec.call("wiki_summary", {"title": title, "lang": "vi"})
            if not result.get("found"):
                return f"Không tìm thấy trang '{title}' trên Wikipedia."
            
            summary = result.get("summary", "")
            url = result.get("url", "")
            
            response = f"Tóm tắt về {title}:\n\n{summary}\n\n"
            if url:
                response += f"Link: {url}"
            
            return response
        except Exception as e:
            return f"Lỗi khi lấy tóm tắt Wikipedia: {str(e)}"

    def mcp_rag_search(query, search_retriever=None):
        """RAG tool được đăng ký như một MCP tool"""
        _retriever = search_retriever or retriever
        if not _retriever:
            return "Xin lỗi, database tìm kiếm chưa được tải. Vui lòng kiểm tra lại file FAISS index."
        
        try:
            query_lower = query.lower()
            relevant_docs = []
            
            # First try vector search
            docs = _retriever.invoke(query)
            
            for d in docs:
                content = d.page_content.strip().lower()
                relevance_score = 0
                
                # Exact phrase matching
                if query_lower in content:
                    relevance_score += 10
                
                # Word matching
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) > 2 and word in content:
                        relevance_score += 2
                
                if relevance_score >= 2:
                    relevant_docs.append((d, relevance_score))
            
            # If no good results, do keyword search across more documents
            if not relevant_docs:
                all_docs = _retriever.vectorstore.similarity_search('đại học', k=50)
                
                for d in all_docs:
                    content = d.page_content.strip().lower()
                    relevance_score = 0
                    
                    query_words = query_lower.split()
                    for word in query_words:
                        if len(word) > 2 and word in content:
                            relevance_score += 1
                    
                    if relevance_score >= 1:
                        relevant_docs.append((d, relevance_score))
            
            # Sort by relevance score
            relevant_docs.sort(key=lambda x: x[1], reverse=True)
            
            if relevant_docs:
                context_parts = []
                for doc, score in relevant_docs[:3]:
                    content = doc.page_content.strip()
                    if len(content) > 50:
                        context_parts.append(content[:500])
                
                context_text = "\n\n".join(context_parts)
                
                return f"Dựa trên thông tin trong database, đây là câu trả lời cho câu hỏi '{query}':\n\n{context_text}"
            else:
                return f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến '{query}' trong database. Database hiện có thông tin về Đại học Cần Thơ, thương hiệu, logo, và các tài liệu liên quan. Bạn có thể thử hỏi về các chủ đề này."
                
        except Exception as e:
            return f"Xin lỗi, có lỗi xảy ra khi tìm kiếm thông tin: {str(e)}"

    # Đăng ký tools
    dispatcher.tools["wiki_search"] = {
        "handler": mcp_wiki_search,
        "description": "Tìm kiếm thông tin trên Wikipedia.",
        "keywords": ["wikipedia", "wiki", "tìm kiếm", "search", "tra cứu", "thông tin về"]
    }

    dispatcher.tools["wiki_summary"] = {
        "handler": mcp_wiki_summary,
        "description": "Lấy tóm tắt từ Wikipedia.",
        "keywords": ["tóm tắt", "summary", "wikipedia", "wiki", "thông tin"]
    }
    
    dispatcher.tools["rag_search"] = {
        "handler": mcp_rag_search,
        "description": "Truy xuất kiến thức từ database nội bộ để trả lời câu hỏi chuyên môn, định nghĩa.",
        "keywords": ["về", "là gì", "tại sao", "thế nào", "như thế nào", "?", "định nghĩa", "tài liệu", "thông tin", "quy định", "máy móc", "hướng dẫn", "ct", "đại học", "logo", "thương hiệu", "e-newsletter", "newsletter", "brand"]
    }
    
    print("Knowledge tools registered successfully")
