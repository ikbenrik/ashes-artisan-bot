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
    "Arcane Engineering", "Armorsmithing", "Carpentry", "Jeweler",
    "Leatherworking", "Scribe", "Tailoring", "Weaponsmithing"
]

PROCESSING = [
    "Alchemy", "Animal Husbandry", "Cooking", "Farming", "Lumbermilling",
    "Metalworking", "Stonemasonry", "Tanning", "Weaving"
]

GATHERING = [
    "Fishing", "Herbalism", "Hunting", "Lumberjacking", "Mining"
]

ALL_ARTISANS = CRAFTING + PROCESSING + GATHERING

# Aliases (short names)
ARTISAN_ALIASES = {
    "ae": "Arcane Engineering",
    "as": "Armorsmithing",
    "cp": "Carpentry",
    "jw": "Jeweler",
    "tl": "Tailoring",
    "lw": "Leatherworking",
    "sc": "Scribe",
    "ws": "Weaponsmithing",
    "al": "Alchemy",
    "ah": "Animal Husbandry",
    "ck": "Cooking",
    "fm": "Farming",
    "lm": "Lumbermilling",
    "mw": "Metalworking",
    "sm": "Stonemasonry",
    "tn": "Tanning",
    "wv": "Weaving",
    "fs": "Fishing",
    "hb": "Herbalism",
    "hn": "Hunting",
    "lj": "Lumberjacking",
    "mn": "Mining"
}

# Combine all names + aliases (optional for autocomplete)
ALL_ARTISANS += list(ARTISAN_ALIASES.keys())

# Resolve alias if needed
def resolve_artisan_name(name):
    name_clean = name.strip().lower()
    return ARTISAN_ALIASES.get(name_clean, name.strip().title())

# Determine artisan type
def get_artisan_type(name):
    full_name = resolve_artisan_name(name)
    if full_name in CRAFTING:
        return "crafting"
    if full_name in PROCESSING:
        return "processing"
    if full_name in GATHERING:
        return "gathering"
    return None

# Find artisan block in the spreadsheet
def find_artisan_block(sheet, artisan_name):
    CRAFTING_COLS = {
        "Arcane Engineering": 2,
        "Armorsmithing": 10,
        "Carpentry": 14,
        "Jeweler": 22,
        "Leatherworking": 6,
        "Scribe": 30,
        "Tailoring": 26,
        "Weaponsmithing": 18
    }

    PROCESSING_COLS = {
        "Alchemy": 44,
        "Animal Husbandry": 39,
        "Cooking": 34,
        "Farming": 49,
        "Lumbermilling": 54,
        "Metalworking": 59,
        "Stonemasonry": 64,
        "Tanning": 69,
        "Weaving": 74
    }

    GATHERING_COLS = {
        "Fishing": 103,
        "Herbalism": 97,
        "Hunting": 91,
        "Lumberjacking": 85,
        "Mining": 79
    }

    artisan_name = resolve_artisan_name(artisan_name)

    if artisan_name in CRAFTING_COLS:
        start_col = CRAFTING_COLS[artisan_name]
        end_col = start_col + 2  # Name, Level, Quality
        artisan_type = "crafting"
    elif artisan_name in PROCESSING_COLS:
        start_col = PROCESSING_COLS[artisan_name]
        end_col = start_col + 3  # Name, Level, Rarity, Quantity
        artisan_type = "processing"
    elif artisan_name in GATHERING_COLS:
        start_col = GATHERING_COLS[artisan_name]
        end_col = start_col + 4  # Name, Level, Rarity, Quantity, Speed
        artisan_type = "gathering"
    else:
        return None

    print(f"[DEBUG] Found '{artisan_name}' — writing from col {start_col} to {end_col} (type: {artisan_type})")

    return {
        "start_col": start_col,
        "end_col": end_col,
        "artisan_type": artisan_type
    }
