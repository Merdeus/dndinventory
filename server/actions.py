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

    await Game.syncPlayerItem(client.gameid, item, isRemoval=True)
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
    curr_player = Player.getFromId(current_item.owner, session)


    log_msg = f"Item {current_item.name} from {curr_player.name} has been deleted by {'Dungeon Master' if client.isDM else 'Player'}"
    target_msg = f"Item {current_item.name} has been deleted by {'Dungeon Master' if client.isDM else 'yourself'}"

    if not (client.isDM or (client.playerid  == current_item.owner)):
        return False, "You are not allowed to delete this item"

    await Game.syncPlayerItem(client.gameid, current_item.id, isRemoval=True)
    await sendMessageToPlayer(current_item.owner,
        {
            "type": "notification",
            "msg": target_msg
        }
    )
    session.delete(current_item)
    session.commit()
    session.close()

    return True, log_msg

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
    
    await Game.updateItemList(client.gameid, session)

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
register_action("AddItem", action_CreateItem)

async def action_SellItem(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    if client.isDM:
        return False, "You are a DM, you can't sell items... duh"
    
    item_id = data["item_id"]
    item = Item.getFromId(item_id, session)

    if not item.isPlayerOwner(client.playerid):
        return False, f"You can't sell an item that is not owned by your player!"
    if item.isQuestItem():
        return False, f"You can't sell a quest item!"
    if not client.isAllowedToSell(item, session):
        return False, f"You are not able to sell anything currently."

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

async def action_GetGameInfo(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    await client.sendGameSync(session)
    return True, ""

register_action("GetGameInfo", action_GetGameInfo)

async def action_ToggleSelling(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    if not client.isDM:
        return False, "You are not a DM, you can't toggle selling"
    
    current_game = Game.getFromId(client.gameid, session)
    current_game.allow_selling = not current_game.allow_selling

    # Notify all players of the game
    for _,client in client_list.items():
        if client is not None and client.gameid == current_game.id:
            await client.send({
                "type": "notification",
                "msg": f"Selling has been toggled to " + ("enabled" if current_game.allow_selling else "disabled")
            })
            await client.send({
                "type": "SellingToggled",
                "msg": current_game.allow_selling
            })

    return True, f"(GameID:{current_game.id}) Selling has been toggled to " + ("enabled" if current_game.allow_selling else "disabled")

register_action("ToggleSelling", action_ToggleSelling)


async def action_SetPlayerGold(client : Client, playerid : int, data, session : sqlalchemy.orm.Session):
    if not client.isDM:
        return False, "You are not a DM, you can't set player gold"
    
    player_id = data.get("player_id", None)
    gold = data.get("gold", None)

    player = Player.getFromId(player_id, session)

    if player is None or gold is None:
        return False, "Player or gold not found"
    
    player.gold = gold
    session.commit()
    await Game.syncPlayerGold(client.gameid, player)
    return True, f"Player {player.name} gold has been set to {gold}"

register_action("SetPlayerGold", action_SetPlayerGold)








#                         case "ImportNewItems":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return

#                             # cooldown
#                             global last_imports
#                             print("ImportNewItems: ", last_imports, self.socket.remote_address[0] in last_imports)
#                             if self.socket.remote_address[0] in last_imports:
#                                 if last_imports[self.socket.remote_address[0]] > (time.time() - 600):
#                                     await self.send(json.dumps({
#                                         "type": "error",
#                                         "msg": "Import cooldown. Chill!"
#                                     }))
#                                     await self.send(json.dumps({
#                                         "type": "items_imported",
#                                         "success": False
#                                     }))
#                                     continue
#                             last_imports[self.socket.remote_address[0]] = time.time()

#                             # ignore which kind of items you actually want to import because there currently is only dnd items
#                             try:
#                                 threading.Thread(target=run_import_script, args=(self.gameid, self.send)).start()

#                             except KeyError as e:
#                                 print("ImportNewItems Error:", e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Invalid ImportNewItems message"
#                                 }))

#                         case "CreatePlayer":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return
#                             try:
#                                 print(msg)
#                                 player_name = msg["player_name"]
#                                 player_gold = msg["gold"]
#                                 if player_name is None or player_name == "" or player_gold is None:
#                                     raise KeyError

#                                 player_gold = max(0, player_gold)
#                                 await registerNewPlayer(player_name, self.gameid, player_gold)
#                             except KeyError as e:
#                                 print(e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Invalid CreatePlayer message"
#                                 }))










#                         case "ClaimLootItem":
#                             print(f"CLAIMLOOTITEM {msg}")
#                             loot_id = msg["loot_id"]
#                             currentLootPool = LootPool.create_new_lootpool(self.gameid)
#                             if currentLootPool.loot.get(loot_id) is None:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": f"Item {loot_id} does not exist!"
#                                 }))
#                                 continue
#                             currentLootPool.setClaim(loot_id, self.playerid)
#                             await currentLootPool.sendLootList()

#                         case "VoteLootItem":

#                             loot_id = msg["loot_id"]
#                             player_id = msg["player_id"]
#                             currentLootPool = LootPool.create_new_lootpool(self.gameid)
#                             if currentLootPool.loot.get(loot_id) is None:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": f"Item {loot_id} does not exist!"
#                                 }))
#                                 continue
#                             session = Session()
#                             try:
#                                 target_player = Player.getFromId(player_id, session)
#                                 if target_player.gameid != self.gameid:
#                                     await self.send(json.dumps({
#                                         "type": "error",
#                                         "msg": f"Invalid VoteLootitem!"
#                                     }))
#                                     return
#                                 try:
#                                     currentLootPool.setVote(loot_id, self.playerid, player_id)
#                                 except:
#                                     print("meh")
#                                 await currentLootPool.sendLootList()
#                             except NotFoundByIDException:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": f"Invalid VoteLootitem!"
#                                 }))
#                                 continue
#                             finally:
#                                 session.close()

#                         case "LootPhaseDone":
#                             currentLootPool = LootPool.create_new_lootpool(self.gameid)
#                             if currentLootPool.phase != LootPool.Phase.CLAIM and currentLootPool.phase != LootPool.Phase.VOTE:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Invalid request"
#                                 }))
#                                 continue

#                             if currentLootPool.handleNewFinish(self.playerid):
#                                 currentLootPool.nextPhase()

#                             await currentLootPool.sendLootList()

#                         case "AddLootItem":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return

#                             item_id = msg["item_id"]
#                             currentLootPool = LootPool.create_new_lootpool(self.gameid)

#                             if currentLootPool.phase.value != 0:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "You can only add loot during the preparations."
#                                 }))
#                                 continue

#                             currentLootPool.addLoot(item_id)
#                             await currentLootPool.sendLootList()

#                         case "RemoveLootItem":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return

#                             loot_id = msg["loot_id"]
#                             currentLootPool = LootPool.create_new_lootpool(self.gameid)
#                             currentLootPool.removeLoot(loot_id)
#                             await currentLootPool.sendLootList()

#                         case "GenerateLootItems":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return

#                             countList = msg["count_list"]
#                             currentLootPool = LootPool.create_new_lootpool(self.gameid)
#                             currentLootPool.generateRandomLoot(countList)
#                             await currentLootPool.sendLootList()

#                         case "SetLootGold":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return
#                             currentLootPool = LootPool.create_new_lootpool(self.gameid)
#                             currentLootPool.gold = msg["loot_gold"]
#                             await currentLootPool.sendLootList()


#                         case "ClearLoot":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return
#                             LootPool.delete_by_gameid(self.gameid)
#                             currentLootPool = LootPool.create_new_lootpool(self.gameid)
#                             await currentLootPool.sendLootList()

#                         case "DistributeLoot":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return

#                             currentLootPool = LootPool.find_by_gameid(self.gameid)
#                             if currentLootPool is None:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "There is no active lootpool"
#                                 }))
#                                 continue

#                             selected_players = msg["players"]
#                             if len(selected_players) < 1:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "You have to select more than one player"
#                                 }))
#                                 continue

#                             if len(currentLootPool.loot) < 1:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "You have to add loot to distribute"
#                                 }))
#                                 continue

#                             session = Session()
#                             try:
#                                 for player in selected_players:
#                                     Player.getFromId(player, session)
#                             except NotFoundByIDException:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Invalid player in player selection"
#                                 }))
#                                 continue

#                             currentLootPool.players = [int(i) for i in selected_players]
#                             currentLootPool.nextPhase()
#                             await currentLootPool.sendLootList()
#                             session.close()