from client import Client
from objects import *
from log import log, logErrorAndNotify
from fastapi import HTTPException
from client import sendMessageToPlayer


registered_actions = {}

def register_action(action_type: str, callback_function):
    if action_type in registered_actions:
        raise ValueError(f"Action {action_type} already registered")
    if not callable(callback_function):
        raise ValueError(f"Callback function is not callable for action {action_type}")
    registered_actions[action_type] = callback_function
    

async def handle_adv_action(action_type : str, client : Client, playerid : int, data):
    if action_type not in registered_actions:
        return False, "Action not found"

    action_session = Session()
    succ, msg = await registered_actions[action_type](client, playerid, data, action_session)
    action_session.close()

    if not succ:
        raise HTTPException(status_code=400, detail=msg)
    
    return msg
    


def give_player_item(gameid, player, item : ItemPrefab, session = None) -> (Item | bool, str):
    if player is None or item is None:
        logErrorAndNotify("Player or item is None. Aborting giving player a item.")
        return False, "Malformed Request"

    curItem = session.query(Item).filter_by(id_prefab=item.id, owner=player.id).first()
    newItem = None

    if item.unique:
        if len(Game.getAllItemsWithPrefabID(gameid, item.id, session)) > 0:
            return False, "This item is unique and is already is in an inventory."

    if curItem is None or not curItem.prefab.stackable:
        newItem = Item(
            id_prefab = item.id,
            count = 1,
            owner = player.id
        )
        session.add(newItem)
    else:
        curItem.count += 1
    session.commit()

    return newItem or curItem, "Player received Item succesfully"


async def action_GiveItem(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    if not client.isDM:
        return False, "You are not a DM, you can't give items to players"
    
    item_id = data.get("item_id", None)
    player_id = data.get("player_id", None)

    item_prefab = ItemPrefab.getFromId(item_id, session)
    player = Player.getFromId(player_id, session)

    if item_prefab is None or player is None:
        return False, "Item or player not found"
    
    item, msg = give_player_item(client.gameid, player, item_prefab, session)

    if not item:
        return False, msg
    await Game.syncPlayerItem(client.gameid, item)
    return True, f"Player {player.name} received item {item.name}"

register_action("GiveItem", action_GiveItem)

async def action_SendItem(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    item_id = data.get("item_id", None)
    target_player_id = data.get("player_id", None)

    item = Item.getFromId(item_id, session)
    player = Player.getFromId(playerid, session)
    target_player = Player.getFromId(target_player_id, session)

    if item is None or player is None or target_player_id is None:
        return False, "Item or player not found"
    
    if not item.isPlayerOwner(client.playerid):
        return False, "You can't send an item that is not owned by your player!"

    item.owner = target_player.id
    session.commit()
    await Game.syncPlayerItem(client.gameid, item)
    await sendMessageToPlayer(target_player_id,
        {
            "type": "notification",
            "msg": f"You have received item {item.name} from player {player.name}"
        }
    )
    return True, f"Item {item.name} has been sent to player {player.name}"

register_action("SendItem", action_SendItem)

async def action_DeleteItem(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    item_id = data.get("item_id", None)
    current_item = Item.getFromId(item_id, session)

    if not (client.isDM or (client.playerid  == current_item.owner)):
        return False, "You are not allowed to delete this item"

    await Game.syncPlayerItem(client.gameid, current_item.id, isRemoval=True)
    session.delete(current_item)
    session.commit()
    session.close()

register_action("DeleteItem", action_DeleteItem)

def edit_item(editItem, session) -> Item | None:
    if editItem is None:
        return None

    try:
        toEditItem = ItemPrefab.getFromId(editItem["id"], session)

        toEditItem.name = editItem["name"]
        toEditItem.type = editItem["itemType"]
        toEditItem.rarity = editItem["rarity"]
        toEditItem.description = editItem["description"]
        toEditItem.value = editItem["value"]
        toEditItem.img = editItem["image"]
        toEditItem.stackable = editItem["isStackable"]
        toEditItem.unique = editItem["isUnique"]

        session.commit()
        return toEditItem

    except NotFoundByIDException as e:
        logErrorAndNotify("Edit item not found")
        return None

async def action_EditItem(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    if not client.isDM:
        return False, "You are not a DM, you can't edit items"
    
    item = data.get("item", None)

    if item is None:
        return False, "Missing data"

    if edit_item(item, session) is None:
        return False, "Failed to edit item"
    
    await Game.updateItemList(client.gameid)

    for item in Game.getAllItemsWithPrefabID(client.gameid, item["id"], session):
        await Game.syncPlayerItem(client.gameid, item)
    
    return True, "Item edited successfully"

register_action("EditItem", action_EditItem)


def create_new_item(name : str, description: str, value : int, img : str, rarity: int, itype: int, gameid : int, session, unique : bool = False, stackable : bool = False) -> bool:
    if name is None or description is None or value is None:
        return False

    session.add(ItemPrefab(
        name=name,
        description=description,
        gameid=gameid,
        value=value,
        rarity=rarity,
        type=itype,
        img=img,
        stackable=stackable,
        unique=unique
    ))
    session.commit()
    log(f"Item {name} [ID: {name}] has been created")
    return True

async def action_CreateItem(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    if not client.isDM:
        return False, "You are not a DM, you can't create items"
    
    item = data.get("item", None)

    if item is None:
        return False, "Missing data"

    name = item.get("name", None)
    description = item.get("description", None)
    value = item.get("value", None)
    img = item.get("image", None)
    rarity = item.get("rarity", None)
    itype = item.get("itemType", None)
    unique = item.get("isUnique", False)
    stackable = item.get("isStackable", False)
    
    if None in [name, description, value, img, rarity, itype]:
        return False, "Missing data"

    if not create_new_item(name, description, value, img, rarity, itype, client.gameid, session, unique, stackable):
        return False, "Failed to create item"
    
    return True, "Item created successfully"

register_action("CreateItem", action_CreateItem)


async def action_SellItem(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    if client.isDM:
        return False, "You are a DM, you can't sell items... duh"
    
    item_id = data["item_id"]
    item = Item.getFromId(item_id, session)

    if not item.isPlayerOwner(client.playerid):
        return False, f"You can't sell an item that is not owned by your player!"
    if item.isQuestItem():
        return False, f"You can't sell a quest item!"
    if not client.isAllowedToSell(item):
        return False, f"You currently are not able to sell anything."

    ply = Player.getFromId(client.playerid, session)
    ply.gold += (item.value * max(item.count,1))

    await Game.syncPlayerItem(client.gameid, item.id, isRemoval=True)
    session.delete(item)
    session.commit()
    await Game.syncPlayerGold(client.gameid, ply)

    message = f'Player {ply.name} sold item "{item.name}" for {item.value} gold'
    log(message)
    return True, message

register_action("SellItem", action_SellItem)