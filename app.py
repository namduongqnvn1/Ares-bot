from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
import os
import json

load_dotenv()

app = Flask(__name__)

# ==== ĐIỀN VÀO FILE .env (không sửa trực tiếp ở đây) ====
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
PAGE_ACCESS_TOKEN = os.environ["PAGE_ACCESS_TOKEN"]
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]

# ==== ID Facebook của những người được quyền dạy bot ====
ADMIN_IDS = [
    "8777624318984889",
]

# 2 lệnh cập nhật riêng biệt:
# "cập nhật 1:" -> sửa RULE / kịch bản giao tiếp (cách bot ứng xử)
# "cập nhật 2:" -> sửa THÔNG TIN quán (giá, giờ, khuyến mãi...)
UPDATE_PREFIX_RULES = "cập nhật 1:"
UPDATE_PREFIX_INFO = "cập nhật 2:"

# Neo đường dẫn theo vị trí file app.py, không phụ thuộc thư mục mày chạy lệnh python từ đâu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(BASE_DIR, "rules.txt")
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "quan_info.txt")
HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")
MAX_HISTORY_MESSAGES = 20

# Nội dung mặc định - chỉ dùng để tạo file lần đầu, sau đó mày sửa trực tiếp trong file
# hoặc bằng lệnh "cập nhật 1:" / "cập nhật 2:" qua chat
DEFAULT_RULES = """1. Trả lời tiếng Việt, giọng gần gũi tự nhiên như nhân viên quán net thật, không máy móc.
2. Mỗi câu trả lời tối đa 2-3 câu, không lan man, không liệt kê dài dòng trừ khi khách hỏi rõ "có những gì".
3. Khi khách khiếu nại/phàn nàn (máy, mạng, đồ ăn...) hoặc muốn cài thêm game chưa có sẵn → xác nhận đã ghi nhận yêu cầu, nhân viên sẽ xử lý/liên hệ lại.
4. TUYỆT ĐỐI không bịa số liệu, giá cả, giờ giấc, khuyến mãi không có trong phần THÔNG TIN QUÁN.
5. Nếu khách nói thông tin cũ khác hiện tại (vd "trước đây quán mở đêm mà") → chỉ xác nhận thông tin HIỆN TẠI nhẹ nhàng, KHÔNG nói "bạn nhớ nhầm" hay "chắc nhầm quán khác".
6. Không tự xưng AI/chatbot trừ khi khách hỏi thẳng.
7. Khách báo đồ để quên → hỏi tuần tự (nếu chưa đủ): (1) mô tả đồ vật, (2) khu vực/số máy ngồi, (3) khoảng thời gian để quên. KHI CHƯA ĐỦ 3 THÔNG TIN: chỉ hỏi câu còn thiếu, TUYỆT ĐỐI KHÔNG nhắc Zalo/SĐT trong lúc này. CHỈ SAU KHI đã đủ cả 3 thông tin → xác nhận đã ghi nhận, rồi mới hướng dẫn liên hệ Zalo quán để được hỗ trợ nhanh hơn.
8. Không trả lời các câu hỏi ngoài chủ đề quán net (chính trị, tôn giáo, nội dung nhạy cảm...) → lịch sự từ chối, lái lại chủ đề quán.
9. Tình trạng máy trống thay đổi liên tục theo thời điểm thực tế. Quán KHÔNG kiểm tra hoặc cam kết máy trống qua tin nhắn và KHÔNG nhận đặt/giữ chỗ trước. Khi khách hỏi, giải thích ngắn gọn, lịch sự và mời khách đến trực tiếp; không hứa "sẽ kiểm tra", "đã giữ máy" hoặc "đã chuyển yêu cầu đặt chỗ".
10. Quán KHÔNG hỗ trợ nạp tiền online. Khách cần đến trực tiếp quầy để nạp tiền và nhận đúng ưu đãi đang áp dụng. Không cung cấp số tài khoản, mã QR, ví điện tử hoặc hướng dẫn chuyển khoản.
11. Khi từ chối một yêu cầu, không trả lời cụt lủn. Cấu trúc câu trả lời: ghi nhận nhu cầu của khách, giải thích lý do ngắn gọn, đưa ra phương án thay thế rõ ràng.
12. Tin nhắn dạng "[Khách vừa gửi 1 ảnh/sticker/video/file...]" → bot không xem được nội dung, hỏi khách mô tả bằng chữ họ cần gì.

CÂU MẪU THAM KHẢO:
Khách hỏi còn máy không: Dạ tình trạng máy trống thay đổi liên tục nên quán chưa thể kiểm tra hoặc cam kết chính xác qua tin nhắn bạn nha. Bạn ghé trực tiếp quán trong khung giờ 7:00–22:00, nhân viên sẽ hỗ trợ sắp xếp máy theo tình trạng thực tế nhé.
Khách muốn đặt hai máy lúc 11 giờ: Dạ quán chưa nhận đặt hoặc giữ máy trước vì tình trạng máy thay đổi liên tục theo thời điểm thực tế bạn nha. Bạn cứ ghé trực tiếp, nhân viên sẽ ưu tiên hỗ trợ sắp xếp các máy gần nhau nếu lúc đó còn phù hợp nhé.
Khách hỏi nạp online: Dạ hiện quán chưa hỗ trợ nạp tiền online bạn nha. Bạn vui lòng ghé trực tiếp quầy để nhân viên nạp đúng tài khoản và áp dụng đầy đủ ưu đãi hiện hành nhé.
Khách bảo ở xa, nhờ giữ máy: Mình hiểu bạn muốn chắc chắn có máy trước khi đến. Tuy nhiên quán chưa thể giữ chỗ vì lượng khách thay đổi liên tục; khi bạn ghé, nhân viên sẽ hỗ trợ sắp xếp nhanh nhất theo tình trạng máy lúc đó nhé."""

DEFAULT_KNOWLEDGE = """Địa chỉ: 168 Lê Hồng Phong, Quy Nhơn
Số máy: 61 máy
Giờ mở cửa: 7h sáng - 22h đêm, KHÔNG mở xuyên đêm

Giá giờ chơi theo khu:
- Standard: 8.680đ/giờ
- VIP: 10.680đ/giờ
- Premium: 12.680đ/giờ
- Arena: 13.680đ/giờ

Số điện thoại / Zalo quán: 0396 886 409"""

SYSTEM_PROMPT_TEMPLATE = """Bạn là nhân viên trực Messenger của quán net Ares Gaming.

THÔNG TIN QUÁN (chỉ dùng đúng số liệu này, không tự suy diễn):
{knowledge}

QUY TẮC GIAO TIẾP:
{rules}"""


def _load_or_create(filepath, default_content):
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(default_content)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def load_rules():
    return _load_or_create(RULES_FILE, DEFAULT_RULES)


def load_knowledge():
    return _load_or_create(KNOWLEDGE_FILE, DEFAULT_KNOWLEDGE)


def append_to_file(filepath, new_line):
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n{new_line}")
    print(f"[DEBUG] Đã ghi vào {filepath}: {new_line}", flush=True)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Sai verify token", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    for entry in data.get("entry", []):
        for msg_event in entry.get("messaging", []):
            sender_id = msg_event["sender"]["id"]
            message = msg_event.get("message", {})

            if "text" in message:
                user_text = message["text"]
            elif "attachments" in message:
                # Khách gửi ảnh/sticker/voice/video/file - không đọc được nội dung,
                # nhưng vẫn phản hồi để khách biết bot đã nhận, không bị im lặng khó chịu
                attachment_type = message["attachments"][0].get("type", "file")
                user_text = f"[Khách vừa gửi 1 {attachment_type}, không có chữ kèm theo]"
            else:
                continue  # bỏ qua các event khác (đã thu hồi tin nhắn, đã đọc...)

            print(f"[DEBUG] sender_id = {sender_id}", flush=True)

            if user_text.strip().lower() == "/whoami":
                send_message(sender_id, f"PSID của bạn là: {sender_id}")
                continue

            if sender_id in ADMIN_IDS:
                text_lower = user_text.lower()

                if text_lower.startswith(UPDATE_PREFIX_RULES):
                    new_rule = user_text[len(UPDATE_PREFIX_RULES):].strip()
                    append_to_file(RULES_FILE, new_rule)
                    send_message(sender_id, f"Đã lưu rule mới: {new_rule}")
                    continue

                if text_lower.startswith(UPDATE_PREFIX_INFO):
                    new_info = user_text[len(UPDATE_PREFIX_INFO):].strip()
                    append_to_file(KNOWLEDGE_FILE, new_info)
                    send_message(sender_id, f"Đã lưu thông tin mới: {new_info}")
                    continue

            reply = ask_ai(sender_id, user_text)
            send_message(sender_id, reply)
    return jsonify({"status": "ok"})


def ask_ai(sender_id, user_text):
    history = load_history()
    conversation = history.get(sender_id, [])
    conversation.append({"role": "user", "content": user_text})
    recent_messages = conversation[-MAX_HISTORY_MESSAGES:]

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        knowledge=load_knowledge(),
        rules=load_rules(),
    )

    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": system_prompt}] + recent_messages,
            "max_tokens": 300,
        },
        timeout=30,
    )
    resp.raise_for_status()
    reply = resp.json()["choices"][0]["message"]["content"]

    conversation.append({"role": "assistant", "content": reply})
    history[sender_id] = conversation
    save_history(history)

    return reply


def send_message(recipient_id, text):
    r = requests.post(
        f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
        json={"recipient": {"id": recipient_id}, "message": {"text": text}},
        timeout=30,
    )
    if r.status_code != 200:
        print("Lỗi gửi tin nhắn:", r.text)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
