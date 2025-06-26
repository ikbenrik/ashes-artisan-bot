import discord
import os
import gspread
import re
from dotenv import load_dotenv

load_dotenv()

from discord import app_commands
from discord.ext import commands
from sheets_helper import connect_sheet, find_artisan_block, get_artisan_type



# ALLOWED_UPDATE_CHANNELS = ["artisan-bot"]
# ALLOWED_VIEW_CHANNELS = ["artisan-bot"]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

def strip_emojis(text):
    return re.sub(r"[^\w\s]", "", text).strip().lower()

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot logged in as {bot.user}")
    print("✅ Slash commands synced successfully.")


@tree.command(name="update", description="Update your artisan skill stats")
@app_commands.describe(
    artisan="Name of the artisan skill (case-insensitive)",
    level="Your level in that skill",
    quality="(Crafting only) Quality rating",
    rarity="(Processing/Gathering) Rarity rating",
    quantity="(Processing/Gathering) Quantity rating",
    speed="(Gathering only) Speed"
)
async def update(interaction: discord.Interaction, artisan: str, level: int = None,
                 quality: int = None, rarity: int = None, quantity: int = None, speed: int = None):

    await interaction.response.defer(ephemeral=True)

    artisan = artisan.strip().title()
    sheet = connect_sheet()
    block = find_artisan_block(sheet, artisan)
    if not block:
        await interaction.followup.send(f"❌ Invalid artisan: **{artisan}**", ephemeral=True)
        return

    user = interaction.user.display_name
    start_col = block["start_col"]
    end_col = block["end_col"]
    artisan_type = block["artisan_type"]

    if artisan_type == "crafting":
        relevant_stats = [("level", level), ("quality", quality)]
    elif artisan_type == "processing":
        relevant_stats = [("level", level), ("rarity", rarity), ("quantity", quantity)]
    elif artisan_type == "gathering":
        relevant_stats = [("level", level), ("rarity", rarity), ("quantity", quantity), ("speed", speed)]
    else:
        await interaction.followup.send("❌ Unknown artisan type.", ephemeral=True)
        return

    if all(value is None for _, value in relevant_stats):
        valid_fields = ", ".join(field for field, _ in relevant_stats)
        await interaction.followup.send(
            f"❌ Please provide at least one of the following for **{artisan}**: {valid_fields}.",
            ephemeral=True
        )
        return

    rows = sheet.get_all_values()
    found_row = None
    insert_row = None

    for row_index in range(7, len(rows)):
        row = rows[row_index]
        if len(row) < start_col:
            continue

        cell = row[start_col - 1]
        if strip_emojis(cell) == strip_emojis(user):
            found_row = row_index
            break
        elif not cell.strip() and insert_row is None:
            insert_row = row_index

    if found_row is not None:
        existing = rows[found_row][start_col - 1:end_col]
        target_row = found_row
    elif insert_row is not None:
        existing = [""] * (end_col - start_col + 1)
        target_row = insert_row
    else:
        existing = [""] * (end_col - start_col + 1)
        target_row = len(rows)

    updated_row = [user] + [
        str(new) if new is not None else existing[i + 1]
        for i, (_, new) in enumerate(relevant_stats)
    ]

    while len(updated_row) < (end_col - start_col + 1):
        updated_row.append("")

    cell_range = f"{gspread.utils.rowcol_to_a1(target_row + 1, start_col)}:{gspread.utils.rowcol_to_a1(target_row + 1, end_col)}"
    sheet.update(cell_range, [updated_row])
    print(f"[DEBUG] Wrote row {target_row + 1} → {updated_row}")

    message = "✅ Updated" if found_row is not None else "✅ Added new entry for"
    await interaction.followup.send(f"{message} **{artisan}**!", ephemeral=True)


@tree.command(name="view_me", description="View your artisan stats")
@app_commands.describe(artisan="(Optional) Specific artisan name to view")
async def view_me(interaction: discord.Interaction, artisan: str = None):

    user = interaction.user.display_name
    sheet = connect_sheet()
    rows = sheet.get_all_values()
    header_row = 6

    result_lines = []
    found = False

    artisan = artisan.title() if artisan else None

    headers = rows[header_row - 1]
    col = 0
    while col < len(headers):
        artisan_name = headers[col].strip()
        artisan_type = get_artisan_type(artisan_name)
        if not artisan_type:
            col += 1
            continue

        if artisan and artisan_name.lower() != artisan.lower():
            col += {"crafting": 3, "processing": 4, "gathering": 5}[artisan_type]
            continue

        col_span = {"crafting": 3, "processing": 4, "gathering": 5}[artisan_type]
        for row_idx in range(header_row, len(rows)):
            row = rows[row_idx]
            if len(row) <= col or strip_emojis(row[col]) != strip_emojis(user):
                continue

            stats = row[col:col + col_span]
            labels = rows[header_row - 1][col:col + col_span]
            display = "\n".join(f"{labels[i]}: {stats[i]}" for i in range(len(labels)))

            result_lines.append(f"**{artisan_name}**\n{display}")
            found = True
            break

        col += col_span

    if not found:
        await interaction.response.send_message(f"❌ No stats found for you{' in ' + artisan if artisan else ''}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"📊 **Your Artisan Stats**:\n" + "\n\n".join(result_lines), ephemeral=True)

@tree.command(name="view_user", description="View another user's artisan stats")
@app_commands.describe(username="The exact display name of the user", artisan="(Optional) Specific artisan to view")
async def view_user(interaction: discord.Interaction, username: str, artisan: str = None):


    await interaction.response.defer(ephemeral=True)  # Defer to avoid timeout

    sheet = connect_sheet()
    rows = sheet.get_all_values()
    header_row = 6

    result_lines = []
    found = False

    artisan = artisan.title() if artisan else None
    headers = rows[header_row - 1]
    col = 0

    while col < len(headers):
        artisan_name = headers[col].strip()
        artisan_type = get_artisan_type(artisan_name)
        if not artisan_type:
            col += 1
            continue

        if artisan and artisan_name.lower() != artisan.lower():
            col += {"crafting": 3, "processing": 4, "gathering": 5}[artisan_type]
            continue

        col_span = {"crafting": 3, "processing": 4, "gathering": 5}[artisan_type]

        for row_idx in range(header_row, len(rows)):
            row = rows[row_idx]
            if len(row) <= col or strip_emojis(row[col]) != strip_emojis(username):
                continue

            stats = row[col:col + col_span]
            labels = rows[header_row - 1][col:col + col_span]
            display = "\n".join(f"{labels[i]}: {stats[i]}" for i in range(len(stats)) if stats[i].strip())
            result_lines.append(f"**{artisan_name}**\n{display}")
            found = True
            break

        col += col_span

    if not found:
        await interaction.followup.send(f"❌ No stats found for **{username}**{' in ' + artisan if artisan else ''}.", ephemeral=True)
    else:
        await interaction.followup.send(f"📊 **{username}'s Artisan Stats**:\n" + "\n\n".join(result_lines), ephemeral=True)

@tree.command(name="view_art", description="View all players with a specific artisan")
@app_commands.describe(artisan="Artisan name to list players for")
async def view_art(interaction: discord.Interaction, artisan: str):

    await interaction.response.defer(ephemeral=True)

    artisan = artisan.strip().title()
    sheet = connect_sheet()
    block = find_artisan_block(sheet, artisan)

    if not block:
        await interaction.followup.send(f"❌ Invalid artisan: **{artisan}**", ephemeral=True)
        return

    rows = sheet.get_all_values()
    header_row = 6
    start_col = block["start_col"]
    end_col = block["end_col"]

    result_lines = []
    for row_idx in range(header_row, len(rows)):
        row = rows[row_idx]
        if len(row) < end_col:
            continue
        name = row[start_col - 1].strip()
        if not name:
            continue

        stats = row[start_col:end_col]  # exclude name column
        labels = rows[header_row - 1][start_col:end_col]  # fetch actual labels from the row ABOVE the data
        stat_text = ", ".join(
           f"{labels[i]}: {stats[i]}" for i in range(len(stats)) if i < len(labels) and stats[i].strip()
        )
        result_lines.append(f"🔹 **{name}** — {stat_text}")

    if result_lines:
        await interaction.followup.send(
            f"📜 **All players with `{artisan}`:**\n" + "\n".join(result_lines),
            ephemeral=True
        )
    else:
        await interaction.followup.send(f"❌ No entries found for `{artisan}`.", ephemeral=True)


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
