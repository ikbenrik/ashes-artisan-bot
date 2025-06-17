import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup the Google Sheets API
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("ashesartisanbot-3fe6703eeb4f.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Vice Artisans").sheet1
    return sheet

# Constants
CRAFTING = [
    "Arcane Engineering", "Armor Smithing", "Carpentry", "Jeweler",
    "Leatherworking", "Scribe", "Tailoring", "Weapon Smithing"
]

PROCESSING = [
    "Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumber Milling",
    "Metalworking", "Stonemasonry", "Tanning", "Weaving"
]

GATHERING = [
    "Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"
]

ALL_ARTISANS = CRAFTING + PROCESSING + GATHERING

# Determine artisan type
def get_artisan_type(name):
    if name in CRAFTING:
        return "crafting"
    if name in PROCESSING:
        return "processing"
    if name in GATHERING:
        return "gathering"
    return None

# Find artisan block in the spreadsheet
def find_artisan_block(sheet, artisan_name):
    header_row = 6
    headers = sheet.row_values(header_row)

    for col_index, cell in enumerate(headers):
        if cell.strip().lower() == artisan_name.strip().lower():
            artisan_type = get_artisan_type(artisan_name)
            if not artisan_type:
                return None

            # Define number of columns based on artisan type
            col_span = {
                "crafting": 3,
                "processing": 4,
                "gathering": 5
            }[artisan_type]

            return {
                "start_col": col_index + 1,
                "end_col": col_index + col_span,
                "artisan_type": artisan_type
            }

    return None
