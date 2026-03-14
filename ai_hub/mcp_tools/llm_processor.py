"""
LLM Processor - Xử lý tương tác với LLM (Ollama)
"""

import json
import time
import threading
import ollama
import re
from asgiref.sync import sync_to_async
from .db_helpers import get_chat_history_async, save_chat_message_async, get_chat_history_sync, save_chat_message_sync

# LLM concurrency control
llm_lock = threading.Lock()


class LLMProcessor:
    """Processor cho việc tương tác với LLM"""
    
    def __init__(self, llm_model, temperature, max_tokens, response_language='vi'):
        self.llm_model = llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.response_language = response_language
    
    def _get_system_prompt(self, selected_tool, device_control_failed=False, is_connection_error=False, is_denied=False):
        """Lấy system prompt phù hợp theo tool được chọn và ngôn ngữ phản hồi"""
        
        lang_map = {
            'vi': 'Tiếng Việt',
            'en': 'Tiếng Anh (English)',
            'ja': 'Tiếng Nhật (Japanese)'
        }
        target_lang = lang_map.get(self.response_language, 'Tiếng Việt')

        base_instruction = f"Bạn là trợ lý AI thông minh của DTHub. QUY TẮC QUAN TRỌNG NHẤT: BẮT BUỘC trả lời toàn bộ nội dung bằng {target_lang}."
        
        if is_denied:
            return (
                f"{base_instruction}\n"
                "QUY TẮC TUYỆT ĐỐI:\n"
                "- Thao tác bị TỪ CHỐI do người dùng chưa kích hoạt công cụ này.\n"
                "- KHÔNG được trả lời câu hỏi chuyên môn bằng kiến thức của bạn.\n"
                "- Hãy thông báo một cách lịch sự rằng công cụ chưa được kích hoạt.\n"
                "- Gợi ý người dùng vào 'Trung tâm Công cụ AI' để kích hoạt công cụ tương ứng.\n"
                "- Trả lời ngắn gọn trong 1-2 câu.\n"
            )
        
        if selected_tool in {"japanese_lookup", "english_define"}:
            return (
                f"{base_instruction}\n"
                "NHIỆM VỤ: Giải thích nghĩa của từ dựa trên TOOL_RESULT.\n"
                "QUY TẮC:\n"
                "- Ưu tiên sử dụng thông tin từ TOOL_RESULT.\n"
                "- Nếu TOOL_RESULT không tìm thấy kết quả (do là câu dài hoặc từ hiếm), bạn ĐƯỢC PHÉP sử dụng kiến thức của mình để dịch hoặc giải thích một cách chính xác.\n"
                f"- Trả lời bằng {target_lang} rõ ràng, ngắn gọn.\n"
                "- Nếu là tiếng Nhật: Hiển thị Kanji và Cách đọc (Reading) nếu có.\n"
                "ĐỊNH DẠNG TRẢ LỜI:\n"
                "- Từ/Cụm từ: <...>\n"
                "- Nghĩa/Dịch: <giải thích hoặc dịch sang ngôn ngữ đích>\n"
            )
        
        elif selected_tool == "rag_search":
            return (
                f"{base_instruction}\n"
                "Bạn là trợ lý tìm kiếm thông tin chuyên môn của DTHub.\n"
                "Bạn sẽ trả lời câu hỏi của người dùng dựa trên thông tin từ TOOL_RESULT (database nội bộ).\n"
                "QUY TẮC BẮT BUỘC:\n"
                "- Chỉ dùng thông tin có trong TOOL_RESULT. Không thêm thông tin ngoài.\n"
                "- Diễn giải lại thông tin một cách rõ ràng, mạch lạc.\n"
                "- Nếu TOOL_RESULT báo không tìm thấy thông tin, hãy nói rõ và gợi ý các chủ đề có sẵn.\n"
                f"- Trả lời bằng {target_lang}, chuyên nghiệp nhưng dễ hiểu.\n"
                "- Giữ lại các nguồn/câu trích dẫn nếu có trong TOOL_RESULT.\n"
            )
        
        elif selected_tool == "device_control" and device_control_failed:
            if is_connection_error:
                return (
                    "Bạn là trợ lý điều khiển thiết bị IoT của DTHub.\n"
                    "Hiện tại thao tác điều khiển THẤT BẠI do lỗi kết nối đến thiết bị.\n"
                    "QUY TẮC:\n"
                    "- Trả lời một cách thân thiện, đồng cảm với người dùng.\n"
                    "- Diễn giải lại thông báo lỗi từ TOOL_RESULT một cách mượt mà, dễ hiểu.\n"
                    "- Giữ nguyên các thông tin quan trọng: tên thiết bị, địa chỉ IP, các bước kiểm tra.\n"
                    "- Có thể sắp xếp lại các bước kiểm tra cho logic hơn.\n"
                    "- Không bịa là đã bật/tắt thành công.\n"
                    "- Không nói 'tôi là mô hình AI' hay các lời khuyên đời thường.\n"
                )
            else:
                return (
                    "Bạn là trợ lý điều khiển thiết bị IoT của DTHub.\n"
                    "Hiện tại thao tác điều khiển THẤT BẠI theo TOOL_RESULT.\n"
                    "QUY TẮC:\n"
                    "- Tuyệt đối không nói kiểu 'tôi là mô hình văn phòng' hay các lời khuyên đời thường.\n"
                    "- Trả lời ngắn gọn: xác nhận có lỗi phía thiết bị/kết nối/cấu hình, dựa đúng TOOL_RESULT.\n"
                    "- Đưa 2-4 bước kiểm tra/khắc phục cụ thể (nhãn thiết bị, online, IP, quyền, v.v.).\n"
                    "- Không bịa là đã bật/tắt thành công.\n"
                )
        
        elif selected_tool == "sensor_read":
            return (
                "Bạn là trợ lý đọc cảm biến IoT của DTHub.\n"
                "NHIỆM VỤ: Trả lời trực tiếp kết quả đọc cảm biến từ TOOL_RESULT.\n"
                "QUY TẮC BẮT BUỘC:\n"
                "- Nếu TOOL_RESULT báo không có dữ liệu/thiết bị offline: nói rõ ràng 'Không có dữ liệu' hoặc 'Thiết bị offline'.\n"
                "- Nếu có dữ liệu: trình bày ngắn gọn giá trị nhiệt độ, độ ẩm (nếu có).\n"
                "- KHÔNG hỏi thêm thông tin từ người dùng.\n"
                "- KHÔNG giải thích dài dòng về hệ thống.\n"
                "- Trả lời trong 1-3 câu.\n"
                "VÍ DỤ:\n"
                "- 'Không có dữ liệu cảm biến nào trong hệ thống.'\n"
                "- 'Thiết bị hiện tại đã offline. Lần cuối ghi nhận: 10 phút trước.'\n"
                "- 'Nhiệt độ: 25.5°C, Độ ẩm: 60%. Dữ liệu đo lúc 14:30.'\n"
            )
        
        elif selected_tool == "weather_info":
            return (
                "Bạn là trợ lý cung cấp thông tin thời tiết của DTHub.\n"
                "NHIỆM VỤ: Trả lời TRỰC TIẾP bằng DỮ LIỆU THỜI TIẾT từ WEATHER_DATA.\n"
                "QUY TẮC TUYỆT ĐỐI:\n"
                "- CHỈ sử dụng DỮ LIỆU từ WEATHER_DATA.\n"
                "- KHÔNG nói 'tôi có thể cung cấp', 'dựa trên dữ liệu', hay bất kỳ lời giới thiệu nào.\n"
                "- Trả lời NGAY LẬP TỨC nhiệt độ, độ ẩm, tình trạng.\n"
                "- KHÔNG hỏi thêm thông tin từ người dùng.\n"
                "- KHÔNG đề cập đến API hay nguồn dữ liệu.\n"
                "VÍ DỤ ĐÚNG:\n"
                "- 'Thời tiết Cần Thơ: 31°C, độ ẩm 82%, nắng.'\n"
                "- 'Hà Nội hiện tại 28°C, có mây, gió 5 km/h.'\n"
            )
        
        else:
            # Default system prompt cho các tool khác
            return (
                "Bạn là trợ lý AI của DTHub.\n"
                "QUY TẮC TRẢ LỜI:\n"
                "- Trả lời TRỰC TIẾP và NGẮN GỌN dựa trên KẾT QUẢ THỰC THI.\n"
                "- KHÔNG hỏi thêm thông tin từ người dùng.\n"
                "- KHÔNG giải thích dài dòng không cần thiết.\n"
                "- Nếu kết quả báo lỗi/không có dữ liệu: nói thẳng ra.\n"
                "- Tối đa 3-4 câu.\n"
            )

    async def generate_plan(self, query: str, chat_history: list, available_tools: list) -> list:
        """
        Giai đoạn 1: Decomposition - Phân tách câu hỏi thành các task nhỏ.
        """
        tools_desc = "\n".join([f"- {t.name}: {t.description} (Schema: {json.dumps(t.mcp_schema, ensure_ascii=False)})" for t in available_tools])
        
        system_prompt = f"""Bạn là Bộ Tổng Quản AI (Orchestrator). 
Nhiệm vụ của bạn là phân tích yêu cầu của người dùng và lập kế hoạch thực thi bằng cách sử dụng các công cụ (tools) có sẵn.

DANH SÁCH CÔNG CỤ:
{tools_desc}
- general_chat: Dùng khi không cần công cụ nào khác hoặc để trả lời trực tiếp.

QUY TẮC LẬP KẾ HOẠCH:
1. Nếu câu hỏi phức tạp, hãy chia nhỏ thành nhiều bước (nhiều tool).
2. Nếu câu hỏi đơn giản, chỉ cần 1 tool.
3. TRẢ VỀ KẾT QUẢ DUY NHẤT DƯỚI DẠNG JSON LIST. KHÔNG GIẢI THÍCH, KHÔNG CHÀO HỎI.
4. Mỗi item trong list có: "tool", "parameters", "reason".

VÍ DỤ:
User: "Bật quạt và tra từ 'học' trong tiếng Nhật"
Output: [
  {{"tool": "device_control", "parameters": {{"device": "quạt", "action": "on"}}, "reason": "Bật quạt theo yêu cầu"}},
  {{"tool": "japanese_lookup", "parameters": {{"keyword": "học"}}, "reason": "Tra từ 'học' trong tiếng Nhật"}}
]
"""
        messages = [
            {"role": "system", "content": system_prompt},
            *chat_history[-3:], 
            {"role": "user", "content": query}
        ]

        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=messages,
                options={"temperature": 0.0}
            )
            content = response['message']['content']
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return [{"tool": "general_chat", "parameters": {"query": query}, "reason": "Fallback to chat"}]
        except Exception as e:
            print(f"[PLAN_ERROR] {e}")
            return [{"tool": "general_chat", "parameters": {"query": query}, "reason": "Error in planning"}]

    async def synthesize_response(self, query: str, results: list, response_language: str = 'vi') -> str:
        """
        Giai đoạn 3: Synthesis - Tổng hợp kết quả từ các task thành câu trả lời cuối cùng.
        """
        lang_map = {'vi': 'Tiếng Việt', 'en': 'Tiếng Anh', 'ja': 'Tiếng Nhật'}
        target_lang = lang_map.get(response_language, 'Tiếng Việt')

        # Kiểm tra xem có kết quả thực tế nào từ tool không
        real_results = [r for r in results if r['tool'] != 'general_chat']
        
        if not real_results:
            system_prompt = f"Bạn là trợ lý AI thân thiện của DTHub. QUY TẮC TUYỆT ĐỐI: BẮT BUỘC trả lời bằng {target_lang}."
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
        else:
            results_str = ""
            for i, r in enumerate(results):
                # Đảm bảo r['result'] là string để prompt sạch sẽ
                res_content = r['result']
                if not isinstance(res_content, str):
                    res_content = json.dumps(res_content, ensure_ascii=False)
                results_str += f"\n--- KẾT QUẢ CÔNG CỤ: {r['tool']} ---\n{res_content}\n"

            system_prompt = f"""Bạn là trợ lý AI của DTHub. 
Nhiệm vụ của bạn là trả lời người dùng DỰA TRÊN DỮ LIỆU THỰC TẾ từ các công cụ.

QUY TẮC TUYỆT ĐỐI (ANTI-HALLUCINATION):
1. CHỈ sử dụng thông tin có trong phần 'DỮ LIỆU THỰC THI'.
2. Nếu dữ liệu công cụ báo 'Không tìm thấy' hoặc trả về lỗi, hãy thông báo đúng như vậy. 
3. TUYỆT ĐỐI KHÔNG tự bịa ra định nghĩa, không suy diễn lung tung từ kiến thức cũ nếu nó mâu thuẫn hoặc không có trong dữ liệu công cụ.
4. BẮT BUỘC trả lời hoàn toàn bằng {target_lang}.
5. Trình bày ngắn gọn, súc tích, chuyên nghiệp.

DỮ LIỆU THỰC THI:
{results_str}
"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]

        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=messages,
                options={"temperature": self.temperature}
            )
            return response['message']['content']
        except Exception as e:
            return f"Lỗi tổng hợp kết quả: {str(e)}"

    async def process_websocket_query(self, consumer, query, session_id, selected_tool, tool_result, user_id=None, is_denied=False):
        """Xử lý query qua WebSocket với streaming (Legacy support)"""
        
        # Check if device control failed
        device_control_failed = False
        is_connection_error = False
        if selected_tool == "device_control" and not is_denied:
            tr = (tool_result or "")
            if not isinstance(tr, str):
                tr = json.dumps(tr, ensure_ascii=False)
            tr_l = tr.lower()
            
            connection_error_markers = [
                "không thể kết nối đến thiết bị", "thiết bị không phản hồi", 
                "thiết bị từ chối kết nối", "không thể thiết lập kết nối sau nhiều lần thử",
                "vui lòng kiểm tra: 1) thiết bị có đang bật và kết nối wifi không"
            ]
            is_connection_error = any(m in tr_l for m in connection_error_markers)
            
            failure_markers = [
                "lỗi", "không thể", "không tìm thấy", "timeout", "không kết nối", "offline",
                "mã lỗi", "error", "failed", "exception",
            ]
            device_control_failed = any(m in tr_l for m in failure_markers)
        
        try:
            start_time = time.time()

            if is_denied:
                full_response = (
                    f"Thao tác bị từ chối: Công cụ '{selected_tool}' chưa được kích hoạt cho tài khoản của bạn. "
                    "Vui lòng truy cập 'Thư viện Công cụ' để kích hoạt trước khi sử dụng."
                )
                if hasattr(consumer, 'send'):
                    await consumer.send(text_data=json.dumps({
                        "type": "chunk", "chunk": full_response, "done": False
                    }, ensure_ascii=False))
                    await consumer.send(text_data=json.dumps({
                        "type": "response", "query": query, "full_response": full_response,
                        "done": True, "tool": selected_tool, "response_time": 0.1
                    }, ensure_ascii=False))
                
                await save_chat_message_async(session_id, query, full_response, tool_used=selected_tool, user_id=user_id)
                return full_response

            with llm_lock:
                chat_history = await get_chat_history_async(session_id or "default", limit=5, user_id=user_id)
                current_time = time.strftime("%H:%M:%S %d/%m/%Y")
                
                lang_map = {'vi': 'Tiếng Việt', 'en': 'Tiếng Anh', 'ja': 'Tiếng Nhật'}
                target_lang = lang_map.get(self.response_language, 'Tiếng Việt')

                base_system_prompt = (
                    f"Bạn là trợ lý AI thông minh của DTHub. Thời gian hiện tại: {current_time}.\n"
                    f"QUY TẮC QUAN TRỌNG: BẮT BUỘC trả lời bằng {target_lang}.\n"
                )
                
                tool_payload = tool_result if isinstance(tool_result, str) else json.dumps(tool_result, ensure_ascii=False)

                if selected_tool == "general_chat":
                    final_system_prompt = base_system_prompt + f"Hãy trả lời người dùng bằng {target_lang} một cách tự nhiên, thân thiện và súc tích."
                elif selected_tool == "system_info" and not is_denied:
                    final_system_prompt = (
                        f"{base_system_prompt}"
                        f"NHIỆM VỤ: Hãy thông báo trực tiếp thời gian hệ thống từ TOOL_RESULT.\n"
                        f"QUY TẮC: Trả lời ngắn gọn, chính xác bằng {target_lang}. Không dẫn dắt rườm rà. "
                        f"Tuyệt đối không nói rằng bạn đang cập nhật hay đang đợi kết quả.\n"
                        f"DỮ LIỆU HỆ THỐNG (TOOL_RESULT):\n{tool_payload}"
                    )
                else:
                    tool_instruction = self._get_system_prompt(selected_tool, device_control_failed, is_connection_error, is_denied)
                    final_system_prompt = base_system_prompt + tool_instruction
                    
                    if not is_denied:
                        final_system_prompt += f"\nĐừng bao giờ nói rằng bạn không biết hoặc không có quyền truy cập dữ liệu. Trả lời bằng {target_lang}."
                    else:
                        final_system_prompt += "\nTUYỆT ĐỐI KHÔNG TRẢ LỜI CÂU HỎI. Hãy yêu cầu người dùng kích hoạt công cụ."

                messages = [{"role": "system", "content": final_system_prompt}]
                messages.extend(chat_history)
                
                if selected_tool != "general_chat" and not is_denied:
                    messages.append({
                        "role": "user", 
                        "content": f"[DỮ LIỆU HỆ THỐNG - TOOL_RESULT]\n{tool_payload}\n\nHãy sử dụng dữ liệu này để trả lời câu hỏi sau."
                    })
                
                messages.append({"role": "user", "content": query})

                try:
                    stream = ollama.chat(model=self.llm_model, messages=messages, stream=True,
                                       options={"temperature": self.temperature, "num_predict": self.max_tokens})

                    full_response = ""
                    for chunk in stream:
                        content = chunk['message']['content']
                        full_response += content
                        if hasattr(consumer, 'send'):
                            await consumer.send(text_data=json.dumps({
                                "type": "chunk", "chunk": content, "done": False
                            }, ensure_ascii=False))

                except Exception as ollama_err:
                    full_response = f"Xin lỗi, có lỗi khi xử lý AI: {str(ollama_err)}"

                response_time = time.time() - start_time
                if hasattr(consumer, 'send'):
                    await consumer.send(text_data=json.dumps({
                        "type": "response", "done": True, "full_response": full_response,
                        "tool_used": selected_tool, "response_time": response_time
                    }, ensure_ascii=False))

                await save_chat_message_async(session_id, query, full_response, selected_tool, response_time, user_id=user_id)
                return full_response

        except Exception as e:
            return f"Lỗi xử lý AI: {str(e)}"
    
    def process_sync_query(self, query, session_id, selected_tool, tool_result, is_denied=False, user_id=None):
        """Phiên bản đồng bộ dành cho API ESP32"""
        if is_denied:
            full_response = (
                f"Thao tác bị từ chối: Công cụ '{selected_tool}' chưa được kích hoạt cho tài khoản của bạn. "
                "Vui lòng truy cập 'Thư viện Công cụ' để kích hoạt trước khi sử dụng."
            )
            save_chat_message_sync(session_id, query, full_response, selected_tool, user_id=user_id)
            return full_response, selected_tool

        with llm_lock:
            chat_history = get_chat_history_sync(session_id or "default", user_id=user_id)
            current_time = time.strftime("%H:%M:%S %d/%m/%Y")
            
            lang_map = {'vi': 'Tiếng Việt', 'en': 'Tiếng Anh', 'ja': 'Tiếng Nhật'}
            target_lang = lang_map.get(self.response_language, 'Tiếng Việt')
            
            base_system_prompt = (
                f"Bạn là trợ lý AI của DTHub. Thời gian hiện tại: {current_time}.\n"
                f"QUY TẮC QUAN TRỌNG: BẮT BUỘC trả lời bằng {target_lang}.\n"
            )

            if selected_tool == "general_chat":
                final_system_prompt = base_system_prompt + "Hãy trả lời người dùng một cách tự nhiên và thân thiện."
                messages = [{"role": "system", "content": final_system_prompt}]
                messages.extend(chat_history)
            else:
                tool_instruction = self._get_system_prompt(selected_tool, is_denied=is_denied)
                final_system_prompt = base_system_prompt + tool_instruction
                messages = [{"role": "system", "content": final_system_prompt}]
                messages.extend(chat_history)
                
                if not is_denied:
                    messages.append({
                        "role": "user", 
                        "content": f"[DỮ LIỆU HỆ THỐNG - TOOL_RESULT]\n{tool_result}\n\nHãy sử dụng dữ liệu này để trả lời câu hỏi sau."
                    })

            messages.append({"role": "user", "content": query})
            
            response = ollama.chat(model=self.llm_model, messages=messages, options={"temperature": self.temperature})
            full_response = response['message']['content']

            save_chat_message_sync(session_id, query, full_response, selected_tool, user_id=user_id)
            return full_response, selected_tool
