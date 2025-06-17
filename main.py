import discord
import os
import gspread
from dotenv import load_dotenv

load_dotenv()

from discord import app_commands
from discord.ext import commands
from sheets_helper import connect_sheet, find_artisan_block, get_artisan_type

ALLOWED_UPDATE_CHANNELS = ["artisan-updates"]
ALLOWED_VIEW_CHANNELS = ["artisan-lookup"]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

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
async def update(interaction: discord.Interaction, artisan: str, level: int,
                 quality: int = None, rarity: int = None, quantity: int = None, speed: int = None):

    channel_name = interaction.channel.name.lower()
    if channel_name not in ALLOWED_UPDATE_CHANNELS:
        await interaction.response.send_message(
            "❌ Please use this command in the #artisan-updates channel.",
            ephemeral=True
        )
        return

    # ⏳ Defer response
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
        if quality is None:
            await interaction.followup.send("❌ Missing `quality` for crafting.", ephemeral=True)
            return
        new_row = [user, str(level), str(quality)]
    elif artisan_type == "processing":
        if rarity is None or quantity is None:
            await interaction.followup.send("❌ Missing `rarity` or `quantity` for processing.", ephemeral=True)
            return
        new_row = [user, str(level), str(rarity), str(quantity)]
    elif artisan_type == "gathering":
        if rarity is None or quantity is None or speed is None:
            await interaction.followup.send("❌ Missing `rarity`, `quantity`, or `speed` for gathering.", ephemeral=True)
            return
        new_row = [user, str(level), str(rarity), str(quantity), str(speed)]
    else:
        await interaction.followup.send("❌ Unknown artisan type.", ephemeral=True)
        return

    rows = sheet.get_all_values()
    for row_index in range(7, len(rows)):
        cell = rows[row_index][start_col - 1]
        if cell.strip().lower() == user.lower():
            sheet.update(
                f"{gspread.utils.rowcol_to_a1(row_index + 1, start_col)}:{gspread.utils.rowcol_to_a1(row_index + 1, end_col)}",
                [new_row]
            )
            await interaction.followup.send(f"✅ Updated your **{artisan}** stats!", ephemeral=True)
            return

    # If user not found, insert in first empty row under the artisan block
    for row_index in range(7, len(rows)):
        cell = rows[row_index][start_col - 1]
        if not cell.strip():
            sheet.update(
                f"{gspread.utils.rowcol_to_a1(row_index + 1, start_col)}:{gspread.utils.rowcol_to_a1(row_index + 1, end_col)}",
                [new_row]
            )
            await interaction.followup.send(f"✅ Added new entry for **{artisan}**!", ephemeral=True)
            return

    # If all else fails, append at bottom
    sheet.append_row([''] * (start_col - 1) + new_row)
    await interaction.followup.send(f"✅ Added new entry for **{artisan}** at the bottom!", ephemeral=True)


@tree.command(name="view_me", description="View your artisan stats")
@app_commands.describe(artisan="(Optional) Specific artisan name to view")
async def view_me(interaction: discord.Interaction, artisan: str = None):
    channel_name = interaction.channel.name.lower()
    if channel_name not in ALLOWED_VIEW_CHANNELS:
        await interaction.response.send_message("❌ Please use this command in the #artisan-lookup channel.", ephemeral=True)
        return

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
            if len(row) <= col or row[col].strip().lower() != user.lower():
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
    channel_name = interaction.channel.name.lower()
    if channel_name not in ALLOWED_VIEW_CHANNELS:
        await interaction.response.send_message("❌ Please use this command in the #artisan-lookup channel.", ephemeral=True)
        return

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
            if len(row) <= col or row[col].strip().lower() != username.lower():
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
    channel_name = interaction.channel.name.lower()
    if channel_name not in ALLOWED_VIEW_CHANNELS:
        await interaction.response.send_message("❌ Please use this command in the #artisan-lookup channel.", ephemeral=True)
        return

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
