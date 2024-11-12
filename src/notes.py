import os
import sqlite3
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import date
from discord.ui import Select, View


# Global dictionary for status emojis
status_emojis = {
    "to-do": "⬜",  # Empty checkbox
    "working on it": "🔄",  # Refresh/Arrow (working on it)
    "completed": "✅"  # Green checkmark
}

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


# Command to list tasks with numbers
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
            tasks_message = "\n".join(f"{index + 1}. {status_emojis.get(status, '❓')} {task}" 
                                     for index, (task, status) in enumerate(tasks))
            await interaction.followup.send(f"Here are your tasks for today:\n{tasks_message}")
        else:
            await interaction.followup.send("You have no tasks for today.")



# Command to update the status of a task
async def update_task_status_command(interaction: discord.Interaction, task_index: int, status: str):
    user_id = interaction.user.id
    today = date.today().isoformat()
    
    # Get the user's tasks
    tasks = get_tasks_by_user(user_id, today)
    
    if not tasks:
        await interaction.response.send_message("You have no tasks for today.")
        return
    
    # Validate task selection
    if task_index < 0 or task_index >= len(tasks):
        await interaction.response.send_message("Invalid task selection.")
        return

    # Update the task status
    task, _ = tasks[task_index]  # Get the selected task
    update_task_status(task, status)  # Update the task status in the database

    await interaction.response.send_message(f"Task '{task}' status updated to '{status}'.")

class StatusSelect(Select):
    def __init__(self, tasks, task_index: int):
        self.tasks = tasks
        self.task_index = task_index
        
        # Create status options for the dropdown
        options = [
            discord.SelectOption(label="To-Do", value="to-do", emoji="⬜"),
            discord.SelectOption(label="Working on it", value="working on it", emoji="🔄"),
            discord.SelectOption(label="Completed", value="completed", emoji="✅")
        ]
        
        super().__init__(placeholder="Select task status", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Get the selected status
        status = self.values[0]
        await update_task_status_command(interaction, self.task_index, status)

# Command to update the status of a task
def update_status(bot: commands.Bot):
    @bot.tree.command(name="update_status", description="Update the status of a task")
    async def update_status_(interaction: discord.Interaction):
        user_id = interaction.user.id
        today = date.today().isoformat()

        # Get the user's tasks for today
        tasks = get_tasks_by_user(user_id, today)
        
        if not tasks:
            await interaction.response.send_message("You have no tasks for today.")
            return
        
        # Create dropdown options with task names and numbers
        task_options = [
            discord.SelectOption(label=f"{index + 1}. {task} ({status_emojis.get(status, '❓')})", value=str(index))
            for index, (task, status) in enumerate(tasks)
        ]
        
        # Create a select dropdown for task selection
        task_select = Select(placeholder="Select a task to update", options=task_options)
        view = View()
        view.add_item(task_select)
        
        # Once a task is selected, show the status update dropdown
        async def task_select_callback(interaction: discord.Interaction):
            selected_task_index = int(task_select.values[0])
            # Create and send the status dropdown
            status_select = StatusSelect(tasks=tasks, task_index=selected_task_index)
            status_view = View()
            status_view.add_item(status_select)
            await interaction.response.send_message(f"Please select the new status for '{tasks[selected_task_index][0]}'.", view=status_view)
        
        # Set the callback to handle task selection
        task_select.callback = task_select_callback

        # Send the message asking to select a task
        await interaction.response.send_message("Please select the task you want to update:", view=view)

