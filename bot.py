import telebot
from telebot import types
import os
from flask import Flask
import threading
import time
from datetime import datetime, timedelta
import psycopg2

# --- তোমার তথ্য এখানে বসানো হয়েছে ---
BOT_TOKEN = "9102581820:AAEkSJcXjx9b2_0Z4PyXHJ14_dbVUai1rTY" 
ADMIN_ID = 8324256407  
BKASH_NUMBER = "01950602111" 
NAGAD_NUMBER = "01950602111" 

# --- Supabase ডেটাবেস লিংক (সরাসরি বসানো) ---
DATABASE_URL = "postgresql://postgres:mitu%40100%4020@db.tiksnhmrqmoometscibr.supabase.co:5432/postgres"

bot = telebot.TeleBot(BOT_TOKEN)

# --- ডেটাবেস সেটআপ (Supabase) ---
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
conn.autocommit = True
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, referrer_id BIGINT, ref_count INTEGER DEFAULT 0, discount INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS panels (id SERIAL PRIMARY KEY, name TEXT, device TEXT, duration TEXT, price TEXT, UNIQUE(name, device, duration, price))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS stock (id SERIAL PRIMARY KEY, panel_name TEXT, duration TEXT, key_code TEXT, is_sold INTEGER DEFAULT 0, sold_at TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id BIGINT, username TEXT, panel_name TEXT, duration TEXT, price TEXT, trx_id TEXT, status TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, discount INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')

cursor.execute("INSERT INTO settings (key, value) VALUES ('referral_active', '1') ON CONFLICT (key) DO NOTHING")
cursor.execute("INSERT INTO settings (key, value) VALUES ('support_contact', '@YourTelegramUsername') ON CONFLICT (key) DO NOTHING")
cursor.execute("INSERT INTO settings (key, value) VALUES ('bkash_number', %s) ON CONFLICT (key) DO NOTHING", (BKASH_NUMBER,))
cursor.execute("INSERT INTO settings (key, value) VALUES ('nagad_number', %s) ON CONFLICT (key) DO NOTHING", (NAGAD_NUMBER,))

initial_panels = [
    ("AIM HACK", "ANDROID - IOS", "1 HOURS", "15 tk"), ("AIM HACK", "ANDROID - IOS", "3 HOURS", "40 tk"),
    ("DRIP WIRE", "ANDROID EXTERNAL", "3 HOURS", "25 tk"), ("DRIP WIRE", "ANDROID EXTERNAL", "7 DAYS", "350 tk"),
    ("ZYRO PANEL", "ANDROID IOS", "1 Hour", "20 tk"), ("ZYRO PANEL", "ANDROID IOS", "1 Day", "120 tk"),
    ("REZZX PANEL", "ANDROID - IOS", "1 Hour", "15 tk"), ("MYTH PANEL", "ANDROID - IOS", "1 Hour", "17 tk"),
    ("HG CHEATS", "NON ROOT", "1 Day", "60 tk"), ("SUPER PROXY iOS", "iOS", "1 Day", "70 tk"),
    ("ANGRY MOD KERNEL", "KERNEL", "1 Day", "90 tk")
]
for p in initial_panels:
    cursor.execute("INSERT INTO panels (name, device, duration, price) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING", p)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Running"

def send_daily_report():
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(*) FROM stock WHERE is_sold=1 AND sold_at LIKE %s", (f"{today}%",))
    sold_today = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stock WHERE is_sold=0")
    available = cursor.fetchone()[0]
    
    report = f"🌙 **ডেইলি রিপোর্ট ({today})**\n\n✅ আজকের সেল: {sold_today} টি কি\n🟡 পেন্ডিং অর্ডার: {pending} টি\n📦 স্টকে আছে: {available} টি\n👥 মোট ইউজার: {total_users} জন"
    try: bot.send_message(ADMIN_ID, report, parse_mode='Markdown')
    except: pass

def report_scheduler():
    while True:
        now = datetime.now()
        target_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        time.sleep(wait_seconds)
        send_daily_report()
        time.sleep(60)

@bot.message_handler(commands=['start'])
def start(message):
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
            if referrer_id != message.from_user.id:
                cursor.execute("SELECT * FROM users WHERE user_id=%s", (message.from_user.id,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO users (user_id, username, referrer_id, ref_count, discount) VALUES (%s, %s, %s, %s, %s)", 
                                   (message.from_user.id, message.from_user.username, referrer_id, 0, 0))
                    cursor.execute("UPDATE users SET ref_count = ref_count + 1 WHERE user_id=%s", (referrer_id,))
                    cursor.execute("SELECT ref_count, discount FROM users WHERE user_id=%s", (referrer_id,))
                    ref_count, discount = cursor.fetchone()
                    if ref_count >= 130 and discount == 0:
                        cursor.execute("UPDATE users SET discount=10 WHERE user_id=%s", (referrer_id,))
                        bot.send_message(referrer_id, "🎉 অভিনন্দন! আপনি ১৩০ জন রেফারেল কমপ্লিট করেছেন। আপনার অ্যাকাউন্টে ১০ টাকা ডিসকাউন্ট যুক্ত হয়েছে!")
        except: pass

    cursor.execute("INSERT INTO users (user_id, username) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING", (message.from_user.id, message.from_user.username))

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🛒 Buy Panels"), types.KeyboardButton("👤 My Profile"))
    markup.add(types.KeyboardButton("📞 Contact Admin"))
    if message.from_user.id == ADMIN_ID:
        markup.add(types.KeyboardButton("⚙️ Admin Panel"))
    bot.send_message(message.chat.id, "স্বাগতম! আমাদের স্টোরে প্যানেল কিনতে নিচের বাটনে ক্লিক করুন।", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📞 Contact Admin")
def contact_admin(message):
    cursor.execute("SELECT value FROM settings WHERE key='support_contact'")
    contact_info = cursor.fetchone()[0]
    msg = bot.send_message(message.chat.id, f"আপনার সমস্যা বা প্রশ্নটি লিখুন। (সরাসরি অ্যাডমিনের কাছে যাবে)\nঅথবা সরাসরি মেসেজ করুন: {contact_info}")
    bot.register_next_step_handler(msg, process_support_message)

def process_support_message(message):
    text = message.text
    bot.send_message(message.chat.id, "✅ আপনার মেসেজ অ্যাডমিনের কাছে পাঠানো হয়েছে।")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("↩️ Reply", callback_data=f"reply_{message.from_user.id}"))
    bot.send_message(ADMIN_ID, f"📩 **নতুন সাপোর্ট!**\n👤 @{message.from_user.username}\n💬 {text}", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def admin_reply(call):
    user_id = int(call.data.split("_")[1])
    msg = bot.send_message(call.message.chat.id, "কাস্টমারকে যে মেসেজ পাঠাতে চান, লিখুন:")
    bot.register_next_step_handler(msg, send_admin_reply, user_id)

def send_admin_reply(message, user_id):
    bot.send_message(user_id, f"📩 **অ্যাডমিনের রিপ্লাই:**\n\n{message.text}")
    bot.send_message(message.chat.id, "✅ রিপ্লাই পাঠানো হয়েছে।")

@bot.message_handler(func=lambda m: m.text == "👤 My Profile")
def profile(message):
    cursor.execute("SELECT ref_count, discount FROM users WHERE user_id=%s", (message.from_user.id,))
    user = cursor.fetchone()
    ref_count = user[0] if user else 0
    discount = user[1] if user else 0
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    text = f"👤 **আপনার প্রোফাইল**\n\n🔗 **রেফারেল লিংক:**\n`{ref_link}`\n\n👥 মোট রেফার: {ref_count}/130\n"
    if discount > 0: text += f"🎁 ডিসকাউন্ট: {discount} টাকা"
    else: text += f"🎁 ১৩০ জন রেফার করলে ১০ টাকা ডিসকাউন্ট পাবেন।"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🛒 Buy Panels")
def show_panel_names(message):
    cursor.execute("SELECT DISTINCT name FROM panels")
    names = cursor.fetchall()
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for name in names:
        cursor.execute("SELECT COUNT(*) FROM stock WHERE panel_name=%s AND is_sold=0", (name[0],))
        if cursor.fetchone()[0] > 0:
            buttons.append(types.InlineKeyboardButton(name[0], callback_data=f"panel_{name[0]}"))
        else:
            buttons.append(types.InlineKeyboardButton(f"{name[0]} (Out of Stock ❌)", callback_data="out_of_stock"))
    markup.add(*buttons)
    bot.send_message(message.chat.id, "আপনি কোন প্যানেলটি কিনতে চান?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "out_of_stock")
def out_of_stock(call):
    bot.answer_callback_query(call.id, "❌ দুঃখিত, এই প্যানেলের সব কি স্টক আউট!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("panel_"))
def show_panel_options(call):
    panel_name = call.data.split("_")[1]
    cursor.execute("SELECT duration, price FROM panels WHERE name=%s", (panel_name,))
    options = cursor.fetchall()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for opt in options:
        markup.add(types.InlineKeyboardButton(f"{opt[0]} - {opt[1]}", callback_data=f"buy_{panel_name}_{opt[0]}_{opt[1]}"))
    bot.edit_message_text(f"📌 **{panel_name}**\n\nপ্যাকেজ সিলেক্ট করুন:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    _, panel_name, duration, price_str = call.data.split("_")
    cursor.execute("SELECT discount FROM users WHERE user_id=%s", (call.from_user.id,))
    user = cursor.fetchone()
    discount = user[0] if user else 0
    price_num = int(''.join(filter(str.isdigit, price_str)))
    final_price = max(0, price_num - discount) 
    
    text = f"✅ আপনি সিলেক্ট করেছেন:\nপ্যানেল: {panel_name}\nসময়: {duration}\n"
    if discount > 0: text += f"🎁 রেফারেল ডিসকাউন্ট: -{discount} tk\n"
    text += f"💵 মোট দাম: {final_price} tk\n\n"
    text += "আপনি কি এটি কিনতে চান? নিচের বাটনে ক্লিক করুন:"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Buy Now", callback_data=f"confirmbuy_{panel_name}_{duration}_{final_price}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_buy")
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "cancel_buy")
def cancel_buy(call):
    bot.edit_message_text("❌ আপনি অর্ডারটি বাতিল করেছেন। আবার শুরু করতে '🛒 Buy Panels' এ ক্লিক করুন।", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirmbuy_"))
def confirm_buy(call):
    _, panel_name, duration, final_price = call.data.split("_")
    final_price = int(final_price)
    
    cursor.execute("INSERT INTO orders (user_id, username, panel_name, duration, price, status) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                   (call.from_user.id, call.from_user.username, panel_name, duration, str(final_price)+" tk", "Waiting_For_Promo"))
    order_id = cursor.fetchone()[0]
    
    text = f"💵 **মোট দাম: {final_price} tk**\n\n"
    text += "🎟️ আপনার কাছে কি কোনো **প্রোমো কোড** আছে? থাকলে লিখুন, না থাকলে `Skip` লিখুন:"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    msg = bot.send_message(call.message.chat.id, "অপেক্ষা করুন...")
    bot.register_next_step_handler(msg, apply_promo_code, order_id, final_price)

def apply_promo_code(message, order_id, current_price):
    code = message.text.strip().upper()
    if code == "SKIP": final_price = current_price
    else:
        cursor.execute("SELECT discount FROM promos WHERE code=%s", (code,))
        promo = cursor.fetchone()
        if promo:
            discount_amt = promo[0]
            final_price = max(0, current_price - discount_amt)
            bot.send_message(message.chat.id, f"✅ প্রোমো কোড সফল! {discount_amt} tk ছাড় পেয়েছেন।")
        else:
            bot.send_message(message.chat.id, "❌ ভুল প্রোমো কোড।")
            final_price = current_price
            
    cursor.execute("UPDATE orders SET price=%s, status='Waiting_For_TrxID' WHERE id=%s", (str(final_price)+" tk", order_id))
    
    cursor.execute("SELECT value FROM settings WHERE key='bkash_number'")
    current_bkash = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM settings WHERE key='nagad_number'")
    current_nagad = cursor.fetchone()[0]
    
    text = f"💵 **ফাইনাল দাম: {final_price} tk**\n\n💳 **পেমেন্ট করুন:**\nবিকাশ: `{current_bkash}`\nনগদ: `{current_nagad}`\n\nটাকা পাঠিয়ে নিচে আপনার **TrxID** লিখে পাঠান:"
    msg = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, receive_trx_id, order_id, final_price)

def receive_trx_id(message, order_id, final_price):
    trx_id = message.text.strip()
    cursor.execute("UPDATE orders SET trx_id=%s, status='Pending' WHERE id=%s", (trx_id, order_id))
    bot.send_message(message.chat.id, "✅ TrxID গ্রহণ করা হয়েছে। অ্যাডমিন অ্যাপ্রুভ করলে কি পাবেন।")
    cursor.execute("SELECT username, panel_name, duration FROM orders WHERE id=%s", (order_id,))
    o = cursor.fetchone()
    admin_text = f"🛒 **নতুন অর্ডার!**\n\n👤 ইউজার: @{o[0]}\n📦 প্যানেল: {o[1]}\n⏱ সময়: {o[2]}\n💵 দাম: {final_price} tk\n🔑 **TrxID: `{trx_id}`**"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Approve & Send Key", callback_data=f"approve_{order_id}"))
    bot.send_message(ADMIN_ID, admin_text, reply_markup=markup, parse_mode='Markdown')

# --- অ্যাডমিন সাইড ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📦 Add Stock (Keys)"), types.KeyboardButton("📋 Pending Orders"))
    markup.add(types.KeyboardButton("📊 Statistics"), types.KeyboardButton("✏️ Edit Price"))
    markup.add(types.KeyboardButton("📢 Broadcast"), types.KeyboardButton("🎟️ Manage Promo Codes"))
    markup.add(types.KeyboardButton("⚙️ Settings"), types.KeyboardButton("🗑 Clear Pending"))
    markup.add(types.KeyboardButton("🔙 Back"))
    bot.send_message(message.chat.id, "অ্যাডমিন প্যানেলে স্বাগতম।", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎟️ Manage Promo Codes" and m.from_user.id == ADMIN_ID)
def manage_promos(message):
    cursor.execute("SELECT code, discount FROM promos")
    promos = cursor.fetchall()
    text = "🎟️ **আপনার প্রোমো কোডগুলো:**\n\n"
    if not promos: text += "কোনো কোড নেই।\n"
    for p in promos: text += f"🔹 `{p[0]}` - {p[1]} tk ডিসকাউন্ট\n"
    text += "\nনতুন কোড যোগ করতে লিখুন: `কোডের_নাম ডিসকাউন্ট_টাকা`\n(যেমন: `EID2024 50`)"
    msg = bot.send_message(message.chat.id, text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, add_promo)

def add_promo(message):
    try:
        code, discount = message.text.split()
        cursor.execute("INSERT INTO promos (code, discount) VALUES (%s, %s) ON CONFLICT (code) DO UPDATE SET discount = EXCLUDED.discount", (code.upper(), int(discount)))
        bot.send_message(message.chat.id, f"✅ প্রোমো কোড `{code.upper()}` যোগ হয়েছে ({discount} tk)!")
    except: bot.send_message(message.chat.id, "❌ ভুল ফরম্যাট।")

@bot.message_handler(func=lambda m: m.text == "⚙️ Settings" and m.from_user.id == ADMIN_ID)
def settings_menu(message):
    cursor.execute("SELECT value FROM settings WHERE key='support_contact'")
    contact = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM settings WHERE key='bkash_number'")
    bkash = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM settings WHERE key='nagad_number'")
    nagad = cursor.fetchone()[0]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 Change Contact Info", callback_data="change_contact"))
    markup.add(types.InlineKeyboardButton("💳 Change bKash Number", callback_data="change_bkash"))
    markup.add(types.InlineKeyboardButton("💳 Change Nagad Number", callback_data="change_nagad"))
    text = f"⚙️ **সেটিংস**\n\n📞 কন্টাক্ট: `{contact}`\n💳 বিকাশ: `{bkash}`\n💳 নগদ: `{nagad}`\n\n(পরিবর্তন করতে বাটনে ক্লিক করুন)"
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "change_contact")
def change_contact_start(call):
    msg = bot.send_message(call.message.chat.id, "নতুন কন্টাক্ট ইনফো দিন:")
    bot.register_next_step_handler(msg, change_contact_save)

def change_contact_save(message):
    cursor.execute("UPDATE settings SET value=%s WHERE key='support_contact'", (message.text,))
    bot.send_message(message.chat.id, f"✅ কন্টাক্ট আপডেট: {message.text}")

@bot.callback_query_handler(func=lambda call: call.data == "change_bkash")
def change_bkash_start(call):
    msg = bot.send_message(call.message.chat.id, "নতুন বিকাশ নাম্বার দিন:")
    bot.register_next_step_handler(msg, change_bkash_save)

def change_bkash_save(message):
    cursor.execute("UPDATE settings SET value=%s WHERE key='bkash_number'", (message.text,))
    bot.send_message(message.chat.id, f"✅ বিকাশ নাম্বার আপডেট: {message.text}")

@bot.callback_query_handler(func=lambda call: call.data == "change_nagad")
def change_nagad_start(call):
    msg = bot.send_message(call.message.chat.id, "নতুন নগদ নাম্বার দিন:")
    bot.register_next_step_handler(msg, change_nagad_save)

def change_nagad_save(message):
    cursor.execute("UPDATE settings SET value=%s WHERE key='nagad_number'", (message.text,))
    bot.send_message(message.chat.id, f"✅ নগদ নাম্বার আপডেট: {message.text}")

@bot.message_handler(func=lambda m: m.text == "📊 Statistics" and m.from_user.id == ADMIN_ID)
def stats(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stock WHERE is_sold=1")
    sold_keys = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stock WHERE is_sold=0")
    available_keys = cursor.fetchone()[0]
    text = f"📊 **স্ট্যাটিসটিক্স**\n\n👥 মোট ইউজার: {total_users} জন\n🟡 পেন্ডিং অর্ডার: {pending} টি\n✅ সোল্ড কি: {sold_keys} টি\n📦 স্টকে আছে: {available_keys} টি"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "✏️ Edit Price" and m.from_user.id == ADMIN_ID)
def edit_price_start(message):
    msg = bot.send_message(message.chat.id, "কোন প্যানেলের দাম পরিবর্তন করবেন? (নাম লিখুন):")
    bot.register_next_step_handler(msg, edit_price_panel)

def edit_price_panel(message):
    panel_name = message.text
    cursor.execute("SELECT duration, price FROM panels WHERE name=%s", (panel_name,))
    opts = cursor.fetchall()
    if not opts: return bot.send_message(message.chat.id, "❌ প্যানেল নেই।")
    text = "কোন প্যাকেজের দাম পরিবর্তন করবেন?\n\n"
    for o in opts: text += f"- {o[0]} (বর্তমান: {o[1]})\n"
    text += "\n(যেমন লিখুন: 1 Day - 150 tk)"
    msg = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(msg, edit_price_update, panel_name)

def edit_price_update(message, panel_name):
    try:
        duration, new_price = message.text.split(" - ")
        cursor.execute("UPDATE panels SET price=%s WHERE name=%s AND duration=%s", (new_price.strip(), panel_name, duration.strip()))
        bot.send_message(message.chat.id, f"✅ নতুন দাম: {new_price.strip()}")
    except: bot.send_message(message.chat.id, "❌ ভুল ফরম্যাট!")

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.from_user.id == ADMIN_ID)
def broadcast_start(message):
    msg = bot.send_message(message.chat.id, "সব ইউজারকে যে মেসেজটি পাঠাতে চান, লিখুন:")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(message):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    success = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **অ্যাডমিন নোটিশ:**\n\n{message.text}", parse_mode='Markdown')
            success += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ মেসেজটি {success} জনকে পাঠানো হয়েছে।")

@bot.message_handler(func=lambda m: m.text == "📋 Pending Orders" and m.from_user.id == ADMIN_ID)
def pending_orders(message):
    cursor.execute("SELECT id, username, panel_name, duration, price, trx_id FROM orders WHERE status='Pending' ORDER BY id DESC")
    orders = cursor.fetchall()
    if not orders: return bot.send_message(message.chat.id, "🎉 কোনো পেন্ডিং নেই।")
    bot.send_message(message.chat.id, f"📋 মোট {len(orders)} টি পেন্ডিং:")
    for o in orders:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{o[0]}"))
        text = f"অর্ডার #{o[0]}\n👤 @{o[1]}\n📦 {o[2]}\n⏱ {o[3]}\n💵 {o[4]}\n🔑 `{o[5]}`"
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🗑 Clear Pending" and m.from_user.id == ADMIN_ID)
def clear_pending(message):
    cursor.execute("DELETE FROM orders WHERE status='Pending'")
    bot.send_message(message.chat.id, "🗑 সব পেন্ডিং মুছে ফেলা হয়েছে!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def approve_order(call):
    order_id = call.data.split("_")[1]
    cursor.execute("SELECT user_id, panel_name, duration FROM orders WHERE id=%s", (order_id,))
    order = cursor.fetchone()
    if not order: return
    user_id, panel_name, duration = order
    
    cursor.execute("SELECT id, key_code FROM stock WHERE panel_name=%s AND duration=%s AND is_sold=0 LIMIT 1", (panel_name, duration))
    stock = cursor.fetchone()
    
    if stock:
        stock_id, key_code = stock
        today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("UPDATE stock SET is_sold=1, sold_at=%s WHERE id=%s", (today, stock_id))
        cursor.execute("UPDATE users SET discount=0 WHERE user_id=%s", (user_id,))
        cursor.execute("DELETE FROM orders WHERE id=%s", (order_id,))
        
        markup = types.InlineKeyboardMarkup(row_width=5)
        for i in range(1, 6): markup.add(types.InlineKeyboardButton(f"{i} ⭐", callback_data=f"rate_{i}"))
        bot.send_message(user_id, f"🎉 অর্ডার অ্যাপ্রুভ!\nপ্যানেল: {panel_name}\nসময়: {duration}\n\n🔑 **কি (Key):** `{key_code}`\n\nরেটিং দিন:", reply_markup=markup, parse_mode='Markdown')
        bot.edit_message_text(f"✅ অর্ডার #{order_id} অ্যাপ্রুভড।", call.message.chat.id, call.message.message_id)
        
        cursor.execute("SELECT COUNT(*) FROM stock WHERE panel_name=%s AND duration=%s AND is_sold=0", (panel_name, duration))
        remaining = cursor.fetchone()[0]
        if remaining <= 5:
            bot.send_message(ADMIN_ID, f"⚠️ **স্টক অ্যালার্ট!**\n{panel_name} ({duration}) স্টক শেষের পথে। আছে {remaining} টি।")
    else:
        bot.send_message(call.message.chat.id, f"⚠️ স্টকে কি নেই!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def handle_rating(call):
    stars = call.data.split("_")[1]
    bot.edit_message_text(f"ধন্যবাদ! আপনি {stars} স্টার দিয়েছেন।", call.message.chat.id, call.message.message_id)
    bot.send_message(ADMIN_ID, f"⭐ **রেটিং!**\n@{call.from_user.username} দিয়েছে: {stars} স্টার।")

@bot.message_handler(func=lambda m: m.text == "📦 Add Stock (Keys)" and m.from_user.id == ADMIN_ID)
def add_stock_start(message):
    msg = bot.send_message(message.chat.id, "কোন প্যানেলের কি অ্যাড করবেন? (নাম লিখুন):")
    bot.register_next_step_handler(msg, add_stock_name)

def add_stock_name(message):
    panel_name = message.text
    msg = bot.send_message(message.chat.id, "কত সময়ের কি? (যেমন: 1 Day):")
    bot.register_next_step_handler(msg, add_stock_duration, panel_name)

def add_stock_duration(message, panel_name):
    duration = message.text
    msg = bot.send_message(message.chat.id, "কি (Key) গুলো দিন (প্রতিটা নতুন লাইনে):")
    bot.register_next_step_handler(msg, add_stock_keys, panel_name, duration)

def add_stock_keys(message, panel_name, duration):
    keys = message.text.split('\n')
    for key in keys:
        if key.strip(): cursor.execute("INSERT INTO stock (panel_name, duration, key_code) VALUES (%s, %s, %s)", (panel_name, duration, key.strip()))
    cursor.execute("SELECT COUNT(*) FROM stock WHERE panel_name=%s AND is_sold=0", (panel_name,))
    stock_count = cursor.fetchone()[0]
    bot.send_message(message.chat.id, f"✅ {len(keys)} টি কি অ্যাড হয়েছে!\n📦 স্টক: {stock_count} টি।")

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def back(message): start(message)

def run_bot(): bot.infinity_polling()
def run_web():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    threading.Thread(target=run_web).start()
    threading.Thread(target=report_scheduler).start()
