games = {}
clientList = []
clients_to_remove = []

from dotenv import load_dotenv
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64
import os

load_dotenv()

discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
global_sync_token_key = os.getenv("SYNC_TOKEN_KEY")
if global_sync_token_key is None:
    global_sync_token_key = "NotReallySecure"

from enum import Enum, auto
class LogLevel(Enum):
    DEBUG = auto()
    INFO = auto()
    ERROR = auto()

loglevel_prefixes = {
    LogLevel.DEBUG: "[DEBUG]",
    LogLevel.INFO: "[INFO]",
    LogLevel.ERROR: "[ERROR]",
}

class ItemRarity(Enum): # not use auto()
    MUNDANE = 0
    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    VERY_RARE = 4
    EPIC = 5
    LEGENDARY = 6
    QUEST_ITEM = 7

item_rarity_names = {
    ItemRarity.COMMON: "Common",
    ItemRarity.UNCOMMON: "Uncommon",
    ItemRarity.RARE: "Rare",
    ItemRarity.VERY_RARE: "Very Rare",
    ItemRarity.EPIC: "Epic",
    ItemRarity.LEGENDARY: "Legendary",
    ItemRarity.QUEST_ITEM: "Quest Item",
}

class ItemType(Enum):
    WEAPON = 1
    ARMOR = 2
    ADVENTURE_GEAR = 3
    TOOL = 4
    CONSUMABLE = 5
    MAGICAL_ITEM = 6
    VALUABLE = 7
    SCROLL = 8
    SHIELD = 9
    RING = 10
    STAFF = 11
    MISC = 12
    WONDROUS = 13

item_type_names = {
    ItemType.WEAPON: "Weapon",
    ItemType.ARMOR: "Armor",
    ItemType.ADVENTURE_GEAR: "Adventure Gear",
    ItemType.TOOL: "Tool",
    ItemType.CONSUMABLE: "Consumable",
    ItemType.MAGICAL_ITEM: "Magical Item",
    ItemType.VALUABLE: "Valuable",
}

def _encrypt(data, key):
    key = key.ljust(32)[:32].encode('utf-8')
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(data.encode('utf-8'), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    encrypted_message = iv + encrypted_data
    return base64.b64encode(encrypted_message).decode('utf-8')

def _decrypt(encrypted_data, key):
    key = key.ljust(32)[:32].encode('utf-8')
    encrypted_data = base64.b64decode(encrypted_data)
    iv = encrypted_data[:AES.block_size]
    encrypted_message = encrypted_data[AES.block_size:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_message), AES.block_size)
    return decrypted_data.decode('utf-8')

def remove_disconnected_clients():
    for client in clients_to_remove:
        try:
            clientList.remove(client)
            del client
        except ValueError:
            pass
    clients_to_remove.clear()

class NotFoundByIDException(BaseException):
    pass