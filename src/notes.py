import os
import sqlite3

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

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
                        task TEXT NOT NULL
                    )''')
        conn.commit()
        conn.close()
        print(f"Created database file: {db_file} and tasks table.")
    else:
        conn = sqlite3.connect(db_file)
        print(f"Connected to database: {db_file}")
    
    return conn


def add(task):
    conn = connect_to_db()
    c = conn.cursor()
    
    c.execute("INSERT INTO tasks (task) VALUES (?)", (task,))
    
    conn.commit()
    conn.close()
    
    print(f"Added note: {task}")

def add_note(bot: commands.Bot):
    @bot.tree.command(name="add", description="Add a task")
    @app_commands.describe(task="The task to add")
    async def add_note_(interaction: discord.Interaction, task: str):
        add(task)
        await interaction.response.send_message(f"Task '{task}' has been added!")
