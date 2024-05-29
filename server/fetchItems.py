import requests
from enum import Enum, auto
from main import create_new_item
import json

toFetchItems = []

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

class ItemRarity(Enum): # not use auto()
    MUNDANE = 0
    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    VERY_RARE = 4
    EPIC = 5
    LEGENDARY = 6
    QUEST_ITEM = 7

rarityLookup = {
    "Common": ItemRarity.COMMON,
    "Uncommon": ItemRarity.UNCOMMON,
    "Rare": ItemRarity.RARE,
    "Very Rare": ItemRarity.VERY_RARE,
    "Epic": ItemRarity.EPIC,
    "Legendary": ItemRarity.LEGENDARY,
    "Artifact": ItemRarity.QUEST_ITEM,
}


typeLookup = {
    "Adventure Gear": ItemType.ADVENTURE_GEAR,
    "Ammunition": ItemType.CONSUMABLE,
    "Arcane Foci": ItemType.MISC,
    "Armor": ItemType.ARMOR,
    "Artisan's Tools": ItemType.TOOL,
    "Druidic Foci": ItemType.MISC,
    "Equipment Packs": ItemType.ADVENTURE_GEAR,
    "Gaming Sets": ItemType.MISC,
    "Heavy Armor": ItemType.ARMOR,
    "Holy Symbols": ItemType.MISC,
    "Kits": ItemType.MISC,
    "Land Vehicles": ItemType.MISC,
    "Martial Melee Weapons": ItemType.WEAPON,
    "Martial Ranged Weapons": ItemType.WEAPON,
    "Martial Weapons": ItemType.WEAPON,
    "Medium Armor": ItemType.ARMOR,
    "Melee Weapons": ItemType.WEAPON,
    "Mounts and Other Animals": ItemType.MISC,
    "Mounts and Vehicles": ItemType.MISC,
    "Musical Instruments": ItemType.MISC,
    "Other Tools": ItemType.TOOL,
    "Potion": ItemType.CONSUMABLE,
    "Ranged Weapons": ItemType.WEAPON,
    "Ring": ItemType.RING,
    "Rod": ItemType.MISC,
    "Scroll": ItemType.SCROLL,
    "Shields": ItemType.SHIELD,
    "Simple Melee Weapons": ItemType.WEAPON,
    "Simple Ranged Weapons": ItemType.WEAPON,
    "Simple Weapons": ItemType.WEAPON,
    "Staff": ItemType.STAFF,
    "Standard Gear": ItemType.ADVENTURE_GEAR,
    "Tack, Harness, and Drawn Vehicles": ItemType.MISC,
    "Tools": ItemType.TOOL,
    "Wand": ItemType.STAFF,
    "Waterborne Vehicles": ItemType.MISC,
    "Weapon": ItemType.WEAPON,
    "Wondrous Items": ItemType.WONDROUS
}

defaultImgType = "https://www.dndbeyond.com/attachments/2/741/potion.jpg"

imgTypes = {
    ItemType.WEAPON: "https://www.dndbeyond.com/attachments/2/742/weapon.jpg",
    ItemType.ARMOR: "https://www.dndbeyond.com/attachments/2/740/armor.jpg",
    ItemType.SCROLL: "https://i.imgur.com/VHPHV9P.jpeg",
    ItemType.WONDROUS: "https://i.imgur.com/JcOSiaU.jpeg"
}

def fetchItem(url, mundane=False):
    citem = requests.get("https://www.dnd5eapi.co" + url).json()
    #print(citem)
    item_name = citem["name"]
    item_type = None

    if "variants" in citem and len(citem["variants"]) > 0:
        print("Item has Variants...")
        for variant in citem["variants"]:
            print(f" - Creating Variant {variant['name']}...")
            fetchItem(variant["url"], mundane=mundane)
        return # this item has variants of it, do not add itself to the list


    try:
        item_type = typeLookup[citem["equipment_category"]["name"]]
    except:
        item_type = ItemType.MISC

    item_img =  imgTypes[item_type] if item_type in imgTypes.keys() else defaultImgType

    item_value = 1
    try:
        unit = citem["cost"]["unit"]
        tmp_value = citem["cost"]["quantity"]
        if unit == "pp":
            tmp_value *= 10
        elif unit == "ep":
            tmp_value /= 2
            tmp_value = round(tmp_value)
        elif unit == "sp":
            tmp_value /= 10
            tmp_value = round(tmp_value)
        elif unit == "cp":
            tmp_value /= 100
            tmp_value = round(tmp_value)

        item_value = tmp_value

    except Exception as e:
        print("Failed to get value: ", e)
        item_value = 1

    item_rarity = ItemRarity.MUNDANE
    if mundane:
        item_rarity = ItemRarity.MUNDANE

    if "rarity" in citem:
        if citem["rarity"]["name"] in rarityLookup:
            item_rarity = rarityLookup[citem["rarity"]["name"]]
        else:
            print(f"{citem['rarity']} not in rarityLookup")


    item_desc = ""

    if "desc" in citem:
        item_desc += "\n".join(citem["desc"])

    if "damage" in citem:
        if item_desc != "":
            item_desc += "\n\n"
        item_desc += citem["damage"]["damage_dice"] + " " + citem["damage"]["damage_type"]["name"]

    if "armor_category" in citem:
        if item_desc != "":
            item_desc += "\n\n"
        item_desc += citem["armor_category"] + " Armor"

    if "armor_class" in citem:
        if item_desc != "":
            item_desc += "\n"

        item_desc += "AC " + str(citem["armor_class"]["base"])
        if "dex_bonus" in citem["armor_class"]:
            if citem["armor_class"]["dex_bonus"]:
                item_desc += " + Dex"
                if "max_bonus" in citem["armor_class"]:
                    item_desc += " (max " + str(citem["armor_class"]["max_bonus"]) + ")"

    if create_new_item(item_name, item_desc, item_value, item_img, item_rarity.value, item_type.value):
        #print(f"Item {item_name} created successfully")
        pass
    else:
        print(f"Item {item_name} failed to be created")

if __name__ == "__main__":

    print(" ")
    print("Creating mundane Items...")
    print(" ")

    items = requests.get("https://www.dnd5eapi.co/api/equipment").json()["results"]
    for item in items:
        fetchItem(item["url"], mundane=True)

    print(" ")
    print(" ")
    print("Creating magical items...")

    items = requests.get("https://www.dnd5eapi.co/api/magic-items").json()["results"]
    for item in items:
        fetchItem(item["url"], mundane=False)

