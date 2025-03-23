from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import sqlite3
from datetime import datetime
import re
import os

TOKEN = "7934570024:AAGW5jyMm-6kp7P2sVHJjhFXsuPcc-ngyew"

# 🔹 Initialize SQLite Database
def init_db():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task TEXT,
            task_time TEXT
        )
    """)
    conn.commit()
    conn.close()

# 🔹 Add Task to Database
def add_task(user_id, task, task_time):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, task, task_time) VALUES (?, ?, ?)", (user_id, task, task_time))
    conn.commit()
    conn.close()

# 🔹 Retrieve Tasks for User
def get_tasks(user_id):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT task, task_time FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

# 🔹 Delete Tasks for User
def delete_tasks(user_id):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# 🔹 Send Reminder
async def send_reminder(context: CallbackContext):
    job = context.job
    await context.bot.send_message(chat_id=job.chat_id, text=f"🔔 Reminder: {job.data['task']} at {job.data['task_time']}")

# 🔹 Schedule Reminder (with improved parameter passing)
def schedule_reminder(application: Application, user_id, task, task_time):
    task_datetime = datetime.strptime(task_time, "%Y-%m-%d %H:%M")
    delay = (task_datetime - datetime.now()).total_seconds()

    if delay > 0:
        application.job_queue.run_once(
            send_reminder, delay, chat_id=user_id, data={"task": task, "task_time": task_time}
        )

        print(f"✅ Task scheduled: {task} at {task_time}")

# 🔹 Load Scheduled Tasks from DB
def load_scheduled_tasks(application: Application):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, task, task_time FROM tasks")
    tasks = cursor.fetchall()
    conn.close()  # ✅ Close DB after fetching tasks

    print(f"🗂️ Found {len(tasks)} tasks to reschedule...")
    for user_id, task, task_time in tasks:
        task_datetime = datetime.strptime(task_time, "%Y-%m-%d %H:%M")
        if task_datetime > datetime.now():  # ✅ Only schedule future tasks
            schedule_reminder(application, user_id, task, task_time)

# 🔹 Command Handlers
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 Welcome! Use:\n"
        "/add <task> <YYYY-MM-DD HH:MM> to add a task\n"
        "/tasks to view tasks\n"
        "/clear to delete all tasks"
    )

async def add(update: Update, context: CallbackContext):
    if len(context.args) < 3:
        await update.message.reply_text("❌ Usage: /add <task> <YYYY-MM-DD HH:MM>")
        return

    task_text = " ".join(context.args[:-2]).strip()
    task_time = " ".join(context.args[-2:]).strip()

    if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", task_time):
        await update.message.reply_text("❌ Invalid format! Use YYYY-MM-DD HH:MM")
        return

    try:
        scheduled_time = datetime.strptime(task_time, "%Y-%m-%d %H:%M")
        if scheduled_time < datetime.now():
            await update.message.reply_text("❌ Cannot schedule a task in the past!")
            return
    except ValueError:
        await update.message.reply_text("❌ Invalid date or time!")
        return

    add_task(update.message.chat_id, task_text, task_time)
    schedule_reminder(context.application, update.message.chat_id, task_text, task_time)
    await update.message.reply_text(f"✅ Task added: {task_text} at {task_time}")

async def tasks(update: Update, context: CallbackContext):
    tasks = get_tasks(update.message.chat_id)
    if not tasks:
        await update.message.reply_text("📭 No tasks found! Add one using /add <task> <YYYY-MM-DD HH:MM>")
    else:
        task_list = "\n".join([f"{t[0]} - {t[1]}" for t in tasks])
        await update.message.reply_text(f"📋 Your Tasks:\n{task_list}")

async def clear(update: Update, context: CallbackContext):
    delete_tasks(update.message.chat_id)
    await update.message.reply_text("🗑️ All tasks cleared!")

async def handle_message(update: Update, context: CallbackContext):
    print("inside the handler---->")
    print(update.message.text)
    user_input = update.message.text.lower()

    text = update.message.text.lower().strip()
    
    if text in ["tasks", "show me the reminders", "show reminders", "my reminders"]:
        return await tasks(update, context) 
    
    # ✅ Regex to detect "remind me to <task> at YYYY-MM-DD HH:MM"
    match = re.search(r"remind me to (.+?) at (\d{4}-\d{2}-\d{2} \d{2}:\d{2})", user_input)

    if match:
        task_text = match.group(1).strip()
        task_time = match.group(2).strip()

        try:
            scheduled_time = datetime.strptime(task_time, "%Y-%m-%d %H:%M")
            if scheduled_time < datetime.now():
                await update.message.reply_text("❌ Cannot schedule a task in the past!")
                return
        except ValueError:
            await update.message.reply_text("❌ Invalid date or time!")
            return

        add_task(update.message.chat_id, task_text, task_time)
        schedule_reminder(context.application, update.message.chat_id, task_text, task_time)
        await update.message.reply_text(f"✅ Task added: {task_text} at {task_time}")
    else:
        await update.message.reply_text("❌ I didn't understand. Try: 'Remind me to drink water at 2025-03-23 20:10'")

# 🔹 Main Function
def main():
    init_db()
    print("🛠️ Database initialized!")

    app = Application.builder().token(TOKEN).build()
    print("🚀 Bot is starting...")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("clear", clear))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # ✅ Handle natural language input

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"(?i)\btasks\b"), tasks))

    load_scheduled_tasks(app)  # ✅ Load tasks from DB on restart

    print("🤖 Bot is running...")
    print("Current Time:", datetime.now().strftime("%Y-%m-%d %H:%M"))
    # app.run_polling()
    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/webhook",
    )

if __name__ == "__main__":
    main()
