from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
import os
import json
import time

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

# Câu trả lời khi AI lỗi - thà nói câu này còn hơn để khách nhắn vào khoảng không
FALLBACK_REPLY = (
    "Dạ bên mình đang hơi trục trặc hệ thống chút xíu, bạn nhắn lại giúp mình sau ít phút nha. "
    "Cần gấp thì bạn gọi Zalo 0396 886 409 nhé!"
)

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
2b. Khi khách hỏi CẤU HÌNH/THÔNG SỐ máy mà KHÔNG nêu tên khu → TUYỆT ĐỐI không liệt kê cả 4 khu. Chỉ trả lời ngắn gọn: quán có 4 khu (Standard, VIP, Premium, Arena), giá từ 8.680đ đến 13.680đ/giờ, rồi hỏi khách muốn xem cấu hình khu nào.
2c. Khi khách đã nêu TÊN KHU cụ thể → trả lời chi tiết đúng cấu hình khu đó (CPU, VGA, RAM, màn hình, chuột, phím, tai nghe) kèm giá và tầng. Chỉ liệt kê cả 4 khu khi khách yêu cầu rõ ràng (vd "cho xem hết", "tất cả các khu").
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

13. Messenger KHÔNG hiển thị định dạng markdown. Viết thuần văn bản: không dùng ** để in đậm, không dùng # hay ` `. Muốn liệt kê thì xuống dòng và dùng dấu gạch đầu dòng "-".

CÂU MẪU THAM KHẢO:
Khách hỏi cấu hình chung chung: Dạ quán mình có 4 khu là Standard, VIP, Premium và Arena, giá từ 8.680đ đến 13.680đ/giờ tuỳ khu nha bạn. Bạn muốn mình gửi cấu hình chi tiết khu nào ạ?
Khách hỏi còn máy không: Dạ tình trạng máy trống thay đổi liên tục nên quán chưa thể kiểm tra hoặc cam kết chính xác qua tin nhắn bạn nha. Bạn ghé trực tiếp quán trong khung giờ 7:00–22:00, nhân viên sẽ hỗ trợ sắp xếp máy theo tình trạng thực tế nhé.
Khách muốn đặt hai máy lúc 11 giờ: Dạ quán chưa nhận đặt hoặc giữ máy trước vì tình trạng máy thay đổi liên tục theo thời điểm thực tế bạn nha. Bạn cứ ghé trực tiếp, nhân viên sẽ ưu tiên hỗ trợ sắp xếp các máy gần nhau nếu lúc đó còn phù hợp nhé.
Khách hỏi nạp online: Dạ hiện quán chưa hỗ trợ nạp tiền online bạn nha. Bạn vui lòng ghé trực tiếp quầy để nhân viên nạp đúng tài khoản và áp dụng đầy đủ ưu đãi hiện hành nhé.
Khách bảo ở xa, nhờ giữ máy: Mình hiểu bạn muốn chắc chắn có máy trước khi đến. Tuy nhiên quán chưa thể giữ chỗ vì lượng khách thay đổi liên tục; khi bạn ghé, nhân viên sẽ hỗ trợ sắp xếp nhanh nhất theo tình trạng máy lúc đó nhé."""

DEFAULT_KNOWLEDGE = """Địa chỉ: 168 Lê Hồng Phong, Quy Nhơn
Số máy: 61 máy
Giờ mở cửa: 7h sáng - 22h đêm, KHÔNG mở xuyên đêm

Quán có 4 khu, chia 2 tầng:
- Tầng trệt: khu STANDARD và khu VIP (quầy tiếp tân ở tầng trệt)
- Tầng 1: khu PREMIUM và khu ARENA

Giá giờ chơi và cấu hình từng khu:

STANDARD - 8.680đ/giờ (tầng trệt)
- CPU i3 đời 12, VGA GTX 1660 Super, RAM 16GB
- Màn hình 24 inch 165Hz
- Chuột Logitech G102 gen 2, bàn phím DareU EK810X, tai nghe DareU 416

VIP - 10.680đ/giờ (tầng trệt)
- CPU i3 đời 12, VGA RTX 2060 Super, RAM 16GB
- Màn hình 27 inch 180Hz
- Chuột Logitech G102 gen 2, bàn phím DareU EK810X, tai nghe DareU 416

PREMIUM - 12.680đ/giờ (tầng 1)
- CPU i5 đời 12, VGA RTX 3060, RAM 32GB
- Màn hình 27 inch 240Hz
- Chuột Logitech G402, bàn phím DareU EK1280X, tai nghe DareU 722X

ARENA - 13.680đ/giờ (tầng 1)
- CPU i5 đời 13, VGA RTX 3060 Ti, RAM 32GB
- Màn hình ZOWIE 25 inch 240Hz
- Chuột ZOWIE S2, bàn phím DareU EK1280X, tai nghe DareU EH925

Số điện thoại / Zalo quán: 0396 886 409"""

SYSTEM_PROMPT_TEMPLATE = """Bạn là nhân viên trực Messenger của quán net Ares Gaming.

THÔNG TIN QUÁN (chỉ dùng đúng số liệu này, không tự suy diễn):
{knowledge}

QUAN TRỌNG - phần THÔNG TIN QUÁN ở trên là nguồn sự thật MỚI NHẤT và luôn đúng.
Thông tin quán được cập nhật liên tục, nên các tin nhắn CŨ trong lịch sử hội thoại có thể
đã lỗi thời. Nếu trước đây bạn từng trả lời là quán KHÔNG có thông tin nào đó (vd cấu hình
máy, giá, dịch vụ) mà bây giờ THÔNG TIN QUÁN đã có, thì phải trả lời theo thông tin hiện tại.
TUYỆT ĐỐI không lặp lại câu từ chối cũ chỉ vì trong lịch sử chat bạn từng nói vậy.

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


@app.route("/", methods=["GET"])
def home():
    # Meta yêu cầu URL trang web trả 200 khi phát hành app, và Render cần
    # 1 endpoint để cron ping giữ service không ngủ
    return """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Ares Gaming Bot</title></head>
<body style="font-family:sans-serif;max-width:640px;margin:60px auto;padding:0 20px">
<h1>Ares Gaming - Trợ lý Messenger</h1>
<p>Đây là dịch vụ webhook tự động trả lời tin nhắn cho Trang Facebook
<strong>Ares Gaming</strong> (quán net, 168 Le Hong Phong, Quy Nhon).</p>
<p>Dịch vụ không có giao diện người dùng. Muốn liên hệ, nhắn tin cho Trang trên Messenger
hoặc Zalo 0396 886 409.</p>
</body></html>""", 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


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

            try:
                reply = ask_ai(sender_id, user_text)
            except Exception as e:
                # DeepSeek lỗi/quá tải - vẫn phải nói gì đó với khách, không được im lặng
                print(f"[LOI AI] {type(e).__name__}: {e}", flush=True)
                reply = FALLBACK_REPLY
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

    # DeepSeek hay trả 429/500/503 lúc quá tải -> thử lại vài lần trước khi bỏ cuộc
    last_error = None
    for attempt in range(3):
        try:
            resp = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "system", "content": system_prompt}] + recent_messages,
                    # 300 khong du cho cau tra loi liet ke cau hinh 4 khu -> bi cat cut giua chung
                    "max_tokens": 800,
                },
                timeout=30,
            )
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            last_error = e
            status = getattr(e.response, "status_code", None)
            # 4xx (trừ 429) là lỗi của mình, thử lại cũng vô ích
            if status is not None and 400 <= status < 500 and status != 429:
                raise
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    else:
        raise last_error

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
