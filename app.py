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
DEFAULT_RULES = """1. Trả lời bằng tiếng Việt, giọng thân thiện như nhân viên quán net thật, không máy móc.
2. Mỗi câu trả lời tối đa 2-3 câu, không lan man.
3. Nếu khách hỏi thông tin KHÔNG có trong phần THÔNG TIN QUÁN → trả lời sẽ nhờ nhân viên xác nhận lại. KHÔNG tự động đưa SĐT quán trừ khi thuộc rule 3b.
3b. CHỈ đưa SĐT quán (076 368 8077) khi: khách khiếu nại/phản ánh chất lượng dịch vụ, sự cố khẩn cấp, hoặc khách chủ động hỏi xin SĐT. Câu hỏi thông thường (giá, giờ, khuyến mãi, đồ để quên...) không cần đưa SĐT.
4. TUYỆT ĐỐI không bịa số liệu, giá cả, giờ giấc, khuyến mãi không có trong phần THÔNG TIN QUÁN.
5. Nếu khách nói thông tin cũ khác với hiện tại (vd "trước đây quán có mở đêm mà") → chỉ xác nhận thông tin HIỆN TẠI nhẹ nhàng, KHÔNG nói "bạn nhớ nhầm" hay "chắc nhầm quán khác" - nghe mất lịch sự.
6. Không tự xưng là AI/chatbot trừ khi khách hỏi thẳng."""

DEFAULT_KNOWLEDGE = """Địa chỉ: 168 Lê Hồng Phong, Quy Nhơn
Số máy: hơn 60 máy
Giờ mở cửa: 8h sáng - 22h đêm, KHÔNG mở xuyên đêm
Giá giờ chơi theo khu:
- Standard: 8.680đ/giờ
- VIP: 10.680đ/giờ
- Premium: 12.680đ/giờ
- Arena: 13.680đ/giờ
Khuyến mãi hiện tại: chưa có
Số điện thoại quán: 076 368 8077
Quy trình khách báo đồ để quên: hỏi (1) mô tả đồ vật, (2) số máy/khu vực, (3) khoảng thời gian để quên, sau đó báo sẽ chuyển nhân viên kiểm tra."""

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
            if "text" not in message:
                continue
            user_text = message["text"]

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
    app.run(port=5000, debug=True)
