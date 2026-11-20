"""
Cấu hình tập trung cho bot.
Tất cả giá trị nhạy cảm lấy từ biến môi trường (Render -> Environment Variables).
"""
import os

# ---------- Token / API ----------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")  # đổi model qua env nếu cần
# Nếu model chính bị Google gỡ (lỗi 404), bot tự thử lần lượt các model này
GEMINI_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash,gemini-2.5-flash-lite").split(",")
    if m.strip()
]
# Model "thinking" tính cả phần suy nghĩ vào giới hạn token -> để dư kẻo câu trả lời bị rỗng
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))
GEMINI_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "60"))
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# ---------- Chủ sở hữu bot (full quyền) ----------
# Điền Discord ID của bạn vào env OWNER_IDS, cách nhau bởi dấu phẩy.
OWNER_IDS = {
    int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip().isdigit()
}

# ---------- Server giữ bot sống trên Render ----------
PORT = int(os.getenv("PORT", "10000"))  # Render tự set PORT; mặc định của Render là 10000
# Render free ngủ sau 15 phút không có request -> bot tự ping URL public của chính nó
KEEPALIVE_URL = os.getenv("KEEPALIVE_URL") or os.getenv("RENDER_EXTERNAL_URL", "")
KEEPALIVE_INTERVAL = int(os.getenv("KEEPALIVE_INTERVAL", "600"))
# Đồng bộ lệnh slash mỗi lần khởi động (đặt SYNC_COMMANDS=0 để tắt khi restart quá nhiều)
SYNC_COMMANDS = os.getenv("SYNC_COMMANDS", "1") != "0"

# ---------- Giới hạn bộ nhớ & file ----------
HISTORY_LENGTH = 12          # số tin nhắn lưu cho mỗi (kênh, người dùng)
MAX_IMAGES_PER_MESSAGE = 4
MAX_IMAGE_BYTES = 6 * 1024 * 1024      # 6 MB
MAX_FILE_BYTES = 1_000_000             # 1 MB
MAX_FILE_CHARS = 3000
MAX_MEMBERS_LISTED = 80
MAX_DISCORD_MSG = 2000                 # giới hạn Discord
TEXT_FILE_EXTENSIONS = ('.txt', '.py', '.json', '.html', '.md',
                        '.csv', '.js', '.cpp', '.java', '.sql', '.yml', '.yaml')

BOT_VERSION = "v5.0.1"
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@admin")

# ---------- Tính cách mặc định của bot ----------
DEFAULT_PERSONA = (
    "Bạn là một bot Discord thân thiện, vui vẻ, nhiệt tình giúp đỡ "
    "mọi người trong server. "
    "Phong cách của bạn hài hước, gần gũi, hay đùa nhẹ và thỉnh thoảng chế diễu "
    "(không xúc phạm cá nhân, không quá đà). "
    "Trả lời ngắn gọn, đi thẳng vào vấn đề, "
    "dùng Markdown khi cần. Nếu bị trêu chọc thì đáp trả dí dỏm nhưng vẫn lịch sự."
)
DEFAULT_LANGUAGE = "Tiếng Việt"
