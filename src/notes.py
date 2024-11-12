import os
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import date

# Database connection and table creation
def connect_to_db():
    db_folder = 'db'
    db_file = os.path.join(db_folder, 'tasks.db')

    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
        print(f"Created folder: {db_folder}")

    if not os.path.exists(db_file):
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        status TEXT DEFAULT 'to-do'
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT NOT NULL
                    )''')
        conn.commit()
        conn.close()
        print(f"Created database file: {db_file} and tables.")
    else:
        conn = sqlite3.connect(db_file)
        print(f"Connected to database: {db_file}")
    
    return conn

# Add a task for a specific user, date, and default status
def add_task_to_db(task, user_id, task_date, status='to-do'):
    conn = connect_to_db()
    c = conn.cursor()
    # Add task to tasks table with default status
    c.execute("INSERT INTO tasks (task, user_id, date, status) VALUES (?, ?, ?, ?)", (task, user_id, task_date, status))
    conn.commit()
    conn.close()
    print(f"Task '{task}' with status '{status}' added for user {user_id} on date {task_date}")

# Ensure user exists in database
def add_user_to_db(user_id, username):
    conn = connect_to_db()
    c = conn.cursor()

    # Check if the user already exists
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()

    if user is None:
        # If user does not exist, add them to the users table
        c.execute("INSERT INTO users (id, username) VALUES (?, ?)", (user_id, username))
        print(f"Added user {username} with ID {user_id}")
    
    conn.commit()
    conn.close()

# Retrieve tasks by user and date with status
def get_tasks_by_user(user_id, task_date):
    conn = connect_to_db()
    c = conn.cursor()
    # Fetch tasks for the given user_id and date
    c.execute("SELECT task, status FROM tasks WHERE user_id = ? AND date = ?", (user_id, task_date))
    tasks = c.fetchall()
    conn.close()
    # Return tasks as a list of tuples (task, status)
    return [(task[0], task[1]) for task in tasks]

# Delete all tasks for the given date
def delete_tasks_for_date(task_date):
    conn = connect_to_db()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE date = ?", (task_date,))
    conn.commit()
    conn.close()
    print(f"Deleted tasks for date {task_date}")

# Update the status of a specific task
def update_task_status(task_id, new_status):
    conn = connect_to_db()
    c = conn.cursor()
    # Update task status
    c.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()
    print(f"Task ID {task_id} status updated to '{new_status}'")

def add_note(bot: commands.Bot):
    @bot.tree.command(name="add", description="Add a task")
    async def add_note_(interaction: discord.Interaction, task: str):
        await interaction.response.defer()  # Defers to prevent timeout
        user = interaction.user
        user_id = user.id
        username = user.name
        today = date.today().isoformat()

        add_user_to_db(user_id, username)
        add_task_to_db(task, user_id, today)

        await interaction.followup.send(f"Task '{task}' has been added for {username} with status 'to-do'.")

def get_note(bot: commands.Bot):
    @bot.tree.command(name="list", description="List today's tasks")
    async def get_note_(interaction: discord.Interaction):
        await interaction.response.defer()  # Defers to prevent timeout
        user_id = interaction.user.id
        today = date.today().isoformat()
        
        tasks = get_tasks_by_user(user_id, today)
        
        # Create a dictionary to map statuses to emojis
        status_emojis = {
            "to-do": "⬜",  # Empty checkbox
            "working on it": "🔄",  # Refresh/Arrow (working on it)
            "completed": "✅"  # Green checkmark
        }


        if tasks:
            tasks_message = "\n".join(f"-{status_emojis.get(status, '❓')} {task}" for task, status in tasks)
            await interaction.followup.send(f"Here are your tasks for today:\n{tasks_message}")
        else:
            await interaction.followup.send("You have no tasks for today.")


# Command to update the status of a task
async def update_status_command(interaction: discord.Interaction, task_id: int, status: str):
    valid_statuses = ["to-do", "working on it", "completed"]
    if status.lower() not in valid_statuses:
        await interaction.response.send_message(f"Invalid status. Choose one of: {', '.join(valid_statuses)}")
        return

    # Update the task status in the database
    update_task_status(task_id, status)
    await interaction.response.send_message(f"Task ID {task_id} status updated to '{status}'.")

def update_status(bot: commands.Bot):
    @bot.tree.command(name="update_status", description="Update the status of a task")
    @app_commands.describe(task_id="The ID of the task to update", status="The new status for the task")
    async def update_status_(interaction: discord.Interaction, task_id: int, status: str):
        await update_status_command(interaction, task_id, status)
