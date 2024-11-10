import os
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

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
                        user_id INTEGER NOT NULL
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

def add_task_to_db(task, user_id):
    conn = connect_to_db()
    c = conn.cursor()
    # Add task to tasks table and link to user
    c.execute("INSERT INTO tasks (task, user_id) VALUES (?, ?)", (task, user_id))
    
    conn.commit()
    conn.close()
    print(f"Task '{task}' added for user {user_id}")

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

# Command to add a task
async def add_note_command(interaction: discord.Interaction, task: str):
    user = interaction.user  # Get the user who triggered the command
    user_id = user.id        # Get the user ID
    username = user.name     # Get the username
    # Add user to the database if not already there
    add_user_to_db(user_id, username)

    # Add task to the database
    add_task_to_db(task, user_id)

    # Respond to the interaction
    await interaction.response.send_message(f"Task '{task}' has been added for {username}.")

def add_note(bot: commands.Bot):
    @bot.tree.command(name="add", description="Add a task")
    @app_commands.describe(task="The task to add")
    async def add_note_(interaction: discord.Interaction, task: str):
        await add_note_command(interaction, task)  # Await and pass interaction and task
