import telebot
import json
from datetime import datetime, timedelta

TOKEN = "توكن_البوت_هنا"
CHANNEL_USERNAME = "@قناتك_الاجبارية"

bot = telebot.TeleBot(TOKEN)
users = {}

MIN_WITHDRAW = 0.0001
TASK_REWARD = 0.000025
DAILY_REWARD = 0.00001
REF_PERCENT = 0.20  # 20%

tasks = [
    {"type": "channel", "title": "اشترك في قناة الجوائز", "url": "https://t.me/examplechannel", "username": "examplechannel"},
    {"type": "bot", "title": "ابدأ هذا البوت", "url": "https://t.me/examplebot", "username": "examplebot"},
    {"type": "group", "title": "انضم لهذه المجموعة", "url": "https://t.me/examplegroup", "username": "examplegroup"}
]

def load_users():
    global users
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except:
        users = {}

def save_users():
    with open("users.json", "w") as f:
        json.dump(users, f)

def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "balance": 0.0,
            "referrals": 0,
            "last_claim": "1970-01-01",
            "tasks_done": [],
            "ref_by": None
        }
    return users[uid]

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🪙 مشاهدة المهام", "🎁 المكافأة اليومية")
    markup.row("💼 رصيدي", "💸 سحب الأرباح")
    markup.row("👥 دعوة الأصدقاء")
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    args = message.text.split()
    if len(args) > 1:
        ref_id = args[1]
        if ref_id != user_id and not user["ref_by"]:
            user["ref_by"] = ref_id
            ref_user = get_user(ref_id)
            ref_user["referrals"] += 1
            save_users()
    try:
        check_sub = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if check_sub.status in ['left']:
            bot.send_message(user_id, f"🚫 يجب عليك الاشتراك في القناة أولاً:\n{CHANNEL_USERNAME}")
            return
    except:
        pass
    bot.send_message(user_id, "✨ مرحبًا بك في بوت ربح TON من المهام والإحالات!\nابدأ الآن واكسب بكل مهمة تنفذها أو صديق تدعوه.",
                     reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🪙 مشاهدة المهام")
def show_tasks(message):
    markup = telebot.types.InlineKeyboardMarkup()
    for task in tasks:
        if task["username"] not in get_user(message.from_user.id)["tasks_done"]:
            markup.add(telebot.types.InlineKeyboardButton(f"{task['title']} ✅", url=task["url"]))
    markup.add(telebot.types.InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_tasks"))
    bot.send_message(message.chat.id, "قم بتنفيذ المهام التالية ثم اضغط تم الاشتراك:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_tasks")
def check_task_subscription(call):
    user = get_user(call.from_user.id)
    done = 0
    for task in tasks:
        try:
            member = bot.get_chat_member("@" + task["username"], call.from_user.id)
            if member.status != "left" and task["username"] not in user["tasks_done"]:
                user["tasks_done"].append(task["username"])
                user["balance"] += TASK_REWARD
                # تحويل نسبة من الربح إلى المُحيل
                if user.get("ref_by"):
                    ref_user = get_user(user["ref_by"])
                    ref_bonus = TASK_REWARD * REF_PERCENT
                    ref_user["balance"] += ref_bonus
                done += 1
        except:
            continue
    save_users()
    bot.answer_callback_query(call.id, f"تم تنفيذ {done} مهمة، وتمت إضافة المكافآت!")

@bot.message_handler(func=lambda m: m.text == "🎁 المكافأة اليومية")
def daily_bonus(message):
    user = get_user(message.from_user.id)
    last = datetime.strptime(user["last_claim"], "%Y-%m-%d")
    today = datetime.utcnow().date()
    if last.date() < today:
        user["balance"] += DAILY_REWARD
        user["last_claim"] = str(today)
        save_users()
        bot.send_message(message.chat.id, "✅ تم إضافة المكافأة اليومية إلى رصيدك!")
    else:
        bot.send_message(message.chat.id, "⏳ لقد استلمت مكافأتك اليوم، عُد غداً!")

@bot.message_handler(func=lambda m: m.text == "💼 رصيدي")
def balance(message):
    user = get_user(message.from_user.id)
    bot.send_message(message.chat.id, f"💰 رصيدك: {user['balance']:.8f} TON\n👥 الإحالات: {user['referrals']}")

@bot.message_handler(func=lambda m: m.text == "💸 سحب الأرباح")
def withdraw_start(message):
    bot.send_message(message.chat.id, "📧 أرسل بريدك الإلكتروني في FaucetPay:")
    bot.register_next_step_handler(message, process_email)

def process_email(message):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        bot.send_message(message.chat.id, "❌ البريد الإلكتروني غير صالح.")
        return
    bot.send_message(message.chat.id, "💰 أرسل الآن المبلغ الذي تريد سحبه:")
    bot.register_next_step_handler(message, process_amount, email)

def process_amount(message, email):
    try:
        amount = float(message.text)
        user = get_user(message.from_user.id)
        if amount > user["balance"]:
            bot.send_message(message.chat.id, "❌ لا تملك هذا الرصيد.")
        elif amount < MIN_WITHDRAW:
            bot.send_message(message.chat.id, f"❌ الحد الأدنى للسحب هو {MIN_WITHDRAW} TON.")
        else:
            user["balance"] -= amount
            save_users()
            bot.send_message(message.chat.id, "✅ تم تنفيذ طلبك، سيتم التحويل خلال دقائق.")
    except:
        bot.send_message(message.chat.id, "❌ أدخل رقمًا صحيحًا.")

@bot.message_handler(func=lambda m: m.text == "👥 دعوة الأصدقاء")
def referral(message):
    uid = message.from_user.id
    link = f"https://t.me/YOUR_BOT_USERNAME?start={uid}"
    msg = f"🔗 شارك هذا الرابط مع أصدقائك واكسب {REF_PERCENT*100:.0f}% من أرباحهم:\n\n{link}"
    bot.send_message(message.chat.id, msg)

load_users()
print("Bot running...")
bot.infinity_polling()
