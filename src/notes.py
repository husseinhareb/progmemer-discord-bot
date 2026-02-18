import os
import sqlite3
import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from datetime import date
from discord.ui import Select, View
from pathlib import Path


# Global dictionary for status emojis
status_emojis = {
    "to-do": "⬜",  # Empty checkbox
    "working on it": "🔄",  # Refresh/Arrow (working on it)
    "completed": "✅"  # Green checkmark
}

# Get absolute path for database
SCRIPT_DIR = Path(__file__).parent.parent.absolute()
DB_FOLDER = SCRIPT_DIR / 'db'
DB_FILE = DB_FOLDER / 'tasks.db'


def ensure_db_exists():
    """Ensure database and tables exist. Does not return a connection."""
    if not DB_FOLDER.exists():
        DB_FOLDER.mkdir(parents=True)
        print(f"Created folder: {DB_FOLDER}")

    with sqlite3.connect(str(DB_FILE)) as conn:
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


def add_task_to_db(task, user_id, task_date, status='to-do'):
    """Add a task for a specific user, date, and default status."""
    with sqlite3.connect(str(DB_FILE)) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO tasks (task, user_id, date, status) VALUES (?, ?, ?, ?)", 
                  (task, user_id, task_date, status))
    print(f"Task '{task}' with status '{status}' added for user {user_id} on date {task_date}")


def add_user_to_db(user_id, username):
    """Ensure user exists in database."""
    with sqlite3.connect(str(DB_FILE)) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()

        if user is None:
            c.execute("INSERT INTO users (id, username) VALUES (?, ?)", (user_id, username))
            print(f"Added user {username} with ID {user_id}")


def get_tasks_by_user(user_id, task_date):
    """Retrieve tasks by user and date with status and ID."""
    with sqlite3.connect(str(DB_FILE)) as conn:
        c = conn.cursor()
        c.execute("SELECT id, task, status FROM tasks WHERE user_id = ? AND date = ?", (user_id, task_date))
        tasks = c.fetchall()
    return [(task[0], task[1], task[2]) for task in tasks]  # (id, task, status)


def update_task_status(task_id, new_status):
    """Update the status of a specific task by its ID."""
    with sqlite3.connect(str(DB_FILE)) as conn:
        c = conn.cursor()

        c.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        if c.rowcount == 0:
            print(f"Task ID {task_id} not found or already set to '{new_status}'.")
        else:
            print(f"Task ID {task_id} successfully updated to status '{new_status}'.")


def add_note(bot: commands.Bot):
    @bot.tree.command(name="add", description="Add a task")
    async def add_note_(interaction: discord.Interaction, task: str):
        await interaction.response.defer()
        user = interaction.user
        user_id = user.id
        username = user.name
        today = date.today().isoformat()

        # Ensure database exists
        ensure_db_exists()
        
        add_user_to_db(user_id, username)
        add_task_to_db(task, user_id, today)

        await interaction.followup.send(f"Task '{task}' has been added for {username} with status 'to-do'.")


def get_note(bot: commands.Bot):
    @bot.tree.command(name="list", description="List tasks for a specific date or today's tasks if no date is provided")
    async def get_note_(interaction: discord.Interaction, day: int = None, month: int = None, year: int = None):
        await interaction.response.defer()

        # Get today's date and use it as a default if parameters are not provided
        today = date.today()
        task_day = day if day is not None else today.day
        task_month = month if month is not None else today.month
        task_year = year if year is not None else today.year
        
        # Construct the date string in 'YYYY-MM-DD' format
        try:
            task_date = date(task_year, task_month, task_day).isoformat()
        except ValueError:
            await interaction.followup.send("Invalid date provided. Please check the day, month, and year.")
            return

        # Ensure database exists
        ensure_db_exists()
        
        user_id = interaction.user.id
        tasks = get_tasks_by_user(user_id, task_date)

        if tasks:
            tasks_message = "\n".join(f"{index + 1}. {status_emojis.get(status, '❓')} {task}" 
                                     for index, (task_id, task, status) in enumerate(tasks))
            await interaction.followup.send(f"Here are your tasks for {task_date}:\n{tasks_message}")
        else:
            await interaction.followup.send(f"You have no tasks for {task_date}.")


async def update_task_status_command(interaction: discord.Interaction, task_id: int, status: str):
    """Command to update the status of a task by its database ID."""
    user_id = interaction.user.id
    today = date.today().isoformat()

    # Ensure database exists
    ensure_db_exists()

    update_task_status(task_id, status)

    # Re-fetch tasks to reflect updated status
    tasks = get_tasks_by_user(user_id, today)
    
    if tasks:
        tasks_message = "\n".join(f"{index + 1}. {status_emojis.get(task_status, '❓')} {task_name}" 
                                 for index, (tid, task_name, task_status) in enumerate(tasks))
        await interaction.response.send_message(f"Task status updated to '{status}'.\n\nHere are your tasks for today:\n{tasks_message}")
    else:
        await interaction.response.send_message(f"Task status updated to '{status}'.")


class StatusSelect(Select):
    def __init__(self, task_id: int):
        self.task_id = task_id
        
        options = [
            discord.SelectOption(label="To-Do", value="to-do", emoji="⬜"),
            discord.SelectOption(label="Working on it", value="working on it", emoji="🔄"),
            discord.SelectOption(label="Completed", value="completed", emoji="✅")
        ]
        
        super().__init__(placeholder="Select task status", options=options)

    async def callback(self, interaction: discord.Interaction):
        status = self.values[0]
        await update_task_status_command(interaction, self.task_id, status)


def _make_task_options(tasks):
    """Create SelectOption list from tasks, truncating labels and limiting to 25.
    Uses task_id (DB primary key) as value for stability."""
    options = []
    for index, (task_id, task, status) in enumerate(tasks[:25]):
        label = f"{index + 1}. {task} ({status_emojis.get(status, '❓')})"
        if len(label) > 100:
            label = label[:97] + "..."
        options.append(discord.SelectOption(label=label, value=str(task_id)))
    return options


def update_status(bot: commands.Bot):
    @bot.tree.command(name="update", description="Update the status of a task")
    async def update_status_(interaction: discord.Interaction):
        user_id = interaction.user.id
        today = date.today().isoformat()

        # Ensure database exists
        ensure_db_exists()
        
        tasks = get_tasks_by_user(user_id, today)
        
        if not tasks:
            await interaction.response.send_message("You have no tasks for today.")
            return
        
        task_options = _make_task_options(tasks)
        
        task_select = Select(placeholder="Select a task to update", options=task_options)
        view = View(timeout=120)  # 2 minute timeout
        view.add_item(task_select)
        
        async def task_select_callback(interaction: discord.Interaction):
            selected_task_id = int(task_select.values[0])
            task_name = next((t[1] for t in tasks if t[0] == selected_task_id), "the task")
            status_select = StatusSelect(task_id=selected_task_id)
            status_view = View(timeout=120)  # 2 minute timeout
            status_view.add_item(status_select)
            await interaction.response.send_message(f"Please select the new status for '{task_name}'.", view=status_view)
        
        task_select.callback = task_select_callback
        await interaction.response.send_message("Please select the task you want to update:", view=view)


def remove_task_from_db(user_id, task_id):
    """Remove a task by its database ID, verifying ownership."""
    # Ensure database exists
    ensure_db_exists()
    
    with sqlite3.connect(str(DB_FILE)) as conn:
        c = conn.cursor()
        c.execute("SELECT task FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        row = c.fetchone()
        if row is None:
            return "Task not found or already removed."
        task_name = row[0]
        c.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    
    return f"Task '{task_name}' has been removed."


def remove_task(bot: commands.Bot):
    @bot.tree.command(name="remove", description="Remove a to-do task for today")
    async def remove_task_(interaction: discord.Interaction):
        user_id = interaction.user.id
        today = date.today().isoformat()
        
        # Ensure database exists
        ensure_db_exists()
        
        tasks = get_tasks_by_user(user_id, today)
        
        if not tasks:
            await interaction.response.send_message("You have no tasks for today.")
            return
        
        task_options = _make_task_options(tasks)
        
        task_select = Select(placeholder="Select a task to remove", options=task_options)
        view = View(timeout=120)  # 2 minute timeout
        view.add_item(task_select)
        
        async def task_select_callback(interaction: discord.Interaction):
            selected_task_id = int(task_select.values[0])
            result = remove_task_from_db(user_id, selected_task_id)
            await interaction.response.send_message(result)
        
        task_select.callback = task_select_callback
        await interaction.response.send_message("Please select the task you want to remove:", view=view)


def edit_task_from_db(user_id, task_id, new_task_description):
    """Edit a task description by its database ID, verifying ownership."""
    # Ensure database exists  
    ensure_db_exists()
    
    with sqlite3.connect(str(DB_FILE)) as conn:
        c = conn.cursor()
        c.execute("SELECT task FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        row = c.fetchone()
        if row is None:
            return "Task not found."
        task_name = row[0]
        c.execute("UPDATE tasks SET task = ? WHERE id = ? AND user_id = ?", 
                  (new_task_description, task_id, user_id))
    
    return f"Task '{task_name}' has been updated to '{new_task_description}'."


def edit_task(bot: commands.Bot):
    @bot.tree.command(name="edit", description="Edit a task description")
    async def edit_task_(interaction: discord.Interaction):
        user_id = interaction.user.id
        today = date.today().isoformat()
        
        # Ensure database exists
        ensure_db_exists()
        
        tasks = get_tasks_by_user(user_id, today)
        
        if not tasks:
            await interaction.response.send_message("You have no tasks for today.")
            return
        
        task_options = _make_task_options(tasks)
        
        task_select = Select(placeholder="Select a task to edit", options=task_options)
        view = View(timeout=120)  # 2 minute timeout
        view.add_item(task_select)
        
        async def task_select_callback(interaction: discord.Interaction):
            selected_task_id = int(task_select.values[0])
            
            await interaction.response.send_message(f"Please enter the new description for the task:")
            
            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id
            
            try:
                msg = await bot.wait_for('message', check=check, timeout=60)
                new_task_description = msg.content
                
                result = edit_task_from_db(user_id, selected_task_id, new_task_description)
                
                await interaction.followup.send(result)
            
            except asyncio.TimeoutError:
                await interaction.followup.send("You took too long to respond. Please try again.")
        
        task_select.callback = task_select_callback
        await interaction.response.send_message("Please select the task you want to edit:", view=view)
