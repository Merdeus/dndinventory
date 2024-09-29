import itertools
import traceback
from typing import List, Type
from xmlrpc.client import Boolean
from sqlalchemy.ext.hybrid import hybrid_property
import threading
import subprocess
import hashlib
import base64

import json
import uuid
import asyncio
import datetime
import time
import random
import websockets
import string
import ssl
import os
import websockets.exceptions

import logging
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from fastapi import FastAPI, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
import uvicorn
from enum import Enum, auto


from objects import Game, Player, Item, ItemPrefab, Session
from util import NotFoundByIDException, LogLevel, loglevel_prefixes, ItemRarity, ItemType, _decrypt, _encrypt, clientList
from log import log, logErrorAndNotify
from client import Client, sendMessageToPlayer
from actions import handle_adv_action

from fastapi.middleware.cors import CORSMiddleware


# tell fastapi that the root begins at /backend
app = FastAPI(root_path="/dnd/backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow your frontend's origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
    
)




client_list = {}
token_list = {}

registration_token_list = {}
random_val = 0

# make next_client_id sync across all async etc.
next_client_id = 0

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)

sockets = []
games = {}
clients_to_remove = []

last_imports = {}

class LootPool:
    _instances = []

    class Phase(Enum):
        PREP = 0
        CLAIM = 1
        VOTE = 2
        CONCLUDED = 3

    def __init__(self, gameid):
        self.gameid = gameid
        self.loot = {}
        self.gold = 0

        self.finished = [] # players who are finished claiming / voting
        self.players = [] # players who should receive anything from this lootpool
        self.votes = []
        self.claims = []

        self.nextLootId = 1
        self.__class__._instances.append(self)

        self.phase = LootPool.Phase.PREP

    def __del__(self):
        try:
            self.__class__._instances.remove(self)
        except ValueError:
            pass

    def addLoot(self, itemid : int):
        self.loot[self.nextLootId] = {}
        self.loot[self.nextLootId]["itemid"] = itemid
        self.loot[self.nextLootId]["claims"] = {}
        self.loot[self.nextLootId]["votes"] = {}
        self.nextLootId += 1

    def removeLoot(self, loot_id : int):
        try:
            del self.loot[loot_id]
        except KeyError:
            pass

    def getToWait(self):
        results = {}
        session = Session()
        current_game = Game.getFromId(self.gameid, session)
        for ply in current_game.players:
            if self.phase == LootPool.Phase.CLAIM:
                if ply.id not in self.finished:
                    if ply.id in self.players:
                        results[ply.id] = ply.name
            elif self.phase == LootPool.Phase.VOTE:
                if ply.id not in self.finished:
                    results[ply.id] = ply.name
        return results

    def handleNewFinish(self, player_id : int) -> bool:
        """Returns True if after the player_id has been added, every player has voted / claimed"""

        # if already "finished" then ignore
        if player_id in self.finished:
            return False

        # if it is the claim phase, only people who are in self.players are allowed to claim / others are ignored
        if self.phase == LootPool.Phase.CLAIM and player_id not in self.players:
            return False

        session = Session()
        current_game = Game.getFromId(self.gameid, session)
        for ply in current_game.players:
            if ply.id == player_id:
                self.finished.append(player_id)
                break

        res = len(current_game.players) == len(self.finished) if self.phase == LootPool.Phase.VOTE else len(self.finished) == len(self.players)
        session.close()
        return res

    def setClaim(self, loot_id : int, player_id : int, unClaim=False):
        if self.phase is not LootPool.Phase.CLAIM:
            return
        if self.loot[loot_id] is None:
            return
        if player_id not in self.players:
            return
        if unClaim:
            self.loot[loot_id]["claims"][player_id] = None
            self.loot[loot_id]["votes"][player_id] = None
            return

        self.loot[loot_id]["claims"][player_id] = True
        self.loot[loot_id]["votes"][player_id] = player_id

    def setVote(self, loot_id : int, voted_player_id : int, vote_player_id : int):
        if self.phase is not LootPool.Phase.VOTE:
            return
        if self.loot[loot_id] is None:
            return
        if voted_player_id not in self.players:
            return # only allow votes for people who are allowed to get this item
        if not self.loot[loot_id]["claims"][voted_player_id]:
            return # only allow votes for people who claim this item

        if self.loot[loot_id]["claims"][vote_player_id]:
            return # if you have claimed an item you automatically vote for yourself
        self.loot[loot_id]["votes"][vote_player_id] = voted_player_id

    def resolve(self) -> (dict | None):
        if self.phase is not LootPool.Phase.VOTE:
            return

        randomBias = {}
        results = {}
        for ply in self.players:
            results[ply] = []
            randomBias[ply] = 0

        for loot_id, vals in enumerate(self.loot):
            if len(vals.claims) == 0:
                # this code basically will give the item to a random player and will record who received it
                # and the next time a random player receives an item, a player who has not received anything will
                # get priority over players who have already received random stuff
                lowest_val = min(randomBias.values())
                keys_lowest_val = [key for key, value in randomBias.items() if value == lowest_val]
                picked_player = random.choice(keys_lowest_val)
                results[picked_player].append(loot_id)
                randomBias[picked_player] += 1
                continue

            if len(vals.claims) == 1:
                claimed_player = next(iter(vals['claims']))
                results[claimed_player].append(loot_id)
                continue

            # there has to be atleast more than one vote because there are more than one claim and if a player claims
            # they automatically vote for themselves

            mostLikely = {}
            for vote in vals.votes:
                mostLikely[vote] = mostLikely.get(vote, 0) + 1

            highest_val = max(mostLikely.values())
            winning_players = [key for key, value in mostLikely.items() if value == highest_val]
            picked_player = random.choice(winning_players)
            results[picked_player].append(loot_id)
            if len(winning_players) > 1:
                randomBias[picked_player] += 1

        return results


    def abortLootPool(self):
        self.__class__._instances.remove(self)
        del self

    def nextPhase(self):
        self.finished = []
        if self.phase is LootPool.Phase.PREP:
            self.phase = LootPool.Phase.CLAIM
        elif self.phase is LootPool.Phase.CLAIM:
            self.phase = LootPool.Phase.VOTE
        elif self.phase is LootPool.Phase.VOTE:
            self.phase = LootPool.Phase.CONCLUDED

    def getLoot(self):
        session = Session()
        loot_list = {}
        try:
            for lootid, vals in self.loot.items():
                item = ItemPrefab.getFromId(vals["itemid"], session)
                loot_list[lootid] = {
                    'id': item.id,
                    'lootid': lootid,
                    'name': item.name,
                    'rarity': item.rarity,
                    'type': item.type,
                    'description': item.description,
                    'value': item.value,
                    'img': item.img,
                    'stackable': item.stackable,
                    'unique': item.unique,
                    'ext': vals
                }
        finally:
            session.close()
        return loot_list

    def generateRandomLoot(self, countList):
        rarity_map = {
            'common': ItemRarity.COMMON,
            'uncommon': ItemRarity.UNCOMMON,
            'rare': ItemRarity.RARE,
            'veryRare': ItemRarity.VERY_RARE,
            'epic': ItemRarity.EPIC,
            'legendary': ItemRarity.LEGENDARY
        }

        session = Session()
        try:
            for rarity_str, rarity_enum in rarity_map.items():
                count = countList.get(rarity_str, 0)
                if count > 0:
                    items = session.query(ItemPrefab).filter_by(gameid=self.gameid, rarity=rarity_enum.value).all()
                    if len(items) < 1:
                        continue
                    for _ in range(min(count, 12)): # vale causec crash
                        if items:
                            item = random.choice(items)
                            self.addLoot(item.id)
        finally:
            session.close()

    async def sendLootList(self, sendToAll=False):


        global clientList
        to_send_list = {
            "type": "loot_list_update",
            "msg": {
                "items": self.getLoot(),
                "gold": self.gold,
                "players": self.players,
                "phase": self.phase.value,
                "waiting": self.getToWait()
            }
        }
        for client in clientList:
            if client.gameid != self.gameid:
                continue
            await client.send(json.dumps(to_send_list))
        remove_disconnected_clients()
    
    @classmethod
    def get_all_instances(cls):
        return cls._instances

    @classmethod
    def find_by_gameid(cls, gameid):
        return next((instance for instance in cls._instances if instance.gameid == gameid), None)

    @classmethod
    def create_new_lootpool(cls, gameid):
        existing = cls.find_by_gameid(gameid)
        if existing:
            return existing
        return cls(gameid)

    @classmethod
    def delete_by_gameid(cls, gameid):
        instance = cls.find_by_gameid(gameid)
        if instance:
            cls._instances.remove(instance)



def run_import_script(gameid, send_callback):
    async def async_run():
        try:
            from fetchItems import importDnDItems
            importDnDItems(gameid)
            await send_callback(json.dumps({
                "type": "items_imported",
                "success": True
            }))
        except Exception as e:
            print("ImportNewItems Error:", e)
            await send_callback(json.dumps({
                "type": "items_imported",
                "success": False
            }))
            await send_callback(json.dumps({
                "type": "error",
                "msg": f"ImportNewItems failed: {str(e)}"
            }))
        await Game.updateItemList(gameid)
    asyncio.run(async_run())

# class Client:
#     def __init__(self, socket, gameid, playerid, isDM=False):
#         self.socket = socket
#         self.gameid = gameid
#         self.playerid = playerid
#         self.isDM = isDM

#     def getInventory(self):
#         session = Session()
#         items = session.query(Item).filter_by(owner=self.playerid).all()
#         inventory = {}

#         for i in items:
#             inventory[i.id] = {
#                 'id': i.id,
#                 'id_prefab': i.id_prefab,
#                 'name': i.name,
#                 'rarity': i.rarity,
#                 'type': i.type,
#                 'description': i.description,
#                 'count': i.count,
#                 'value': i.value,
#                 'img': i.img,
#                 'stackable': i.prefab.stackable,
#                 'unique': i.prefab.unique
#             }
#         session.close()
#         return inventory

#     def getInventories(self):
#         session = Session()

#         try:
#             current_game = Game.getFromId(self.gameid, session)

#             # Retrieve all players associated with the current game
#             players = session.query(Player).filter_by(gameid=current_game.id).all()

#             # Initialize a dictionary to hold all inventories
#             all_inventories = {}

#             # For each player, retrieve their inventory
#             for player in players:
#                 tmp = session.query(Item).filter_by(owner=player.id).all()
#                 inventory = {}
#                 for i in tmp:
#                     inventory[i.id] = {
#                         'id': i.id,
#                         'id_prefab': i.id_prefab,
#                         'name': i.name,
#                         'rarity': i.rarity,
#                         'type': i.type,
#                         'description': i.description,
#                         'count': i.count,
#                         'value': i.value,
#                         'img': i.img,
#                         'stackable': i.prefab.stackable,
#                         'unique': i.prefab.unique
#                     }

#                 # Add the player's inventory to the all_inventories dictionary
#                 all_inventories[player.id] = {
#                     'id': player.id,
#                     'name': player.name,
#                     'gold': player.gold,
#                     'inventory': inventory
#                 }

#             return all_inventories
#         finally:
#             session.close()

#     def isAllowedToSell(self, item : Item) -> bool:
#         if self.isDM:
#             return False
#         # TODO: Add check that global sell is active and item is not a questitem
#         return True


#     async def SellItem(self, item : Item, session) -> (bool, str):
#         if self.isDM:
#             return False, "You are a DM, you can't sell items... duh"
#         if not item.isPlayerOwner(self.playerid):
#             return False, f"You can't sell an item that is not owned by your player!"
#         if item.isQuestItem():
#             return False, f"You can't sell a quest item!"
#         if not self.isAllowedToSell(item):
#             return False, f"You currently are not able to sell anything."

#         ply = Player.getFromId(self.playerid, session)

#         ply.gold += (item.value * max(item.count,1))

#         await Game.syncPlayerItem(self.gameid, item.id, isRemoval=True)
#         session.delete(item)
#         session.commit()
#         await Game.syncPlayerGold(self.gameid, ply)

#         message = f'Player {ply.name} sold item "{item.name}" for {item.value} gold'
#         log(message)
#         return True, message

#     def SendItem(self, item : Item, toSentplayer : int, session) -> (bool, string):
#         # maybe check if both players are part of the same game?
#         if not self.isDM and not item.isPlayerOwner(self.playerid):
#             return False, f"You don't own this item!"

#         return True, ""

#     def DestroyItem(self, item : int) -> (bool, str):

#         session = Session()
#         item = Item.getFromId(item)
#         ply = Player.getFromId(self.playerid, session)
#         if item is None:
#             return False, f"This item does not exist!"

#         if item.isQuestItem():
#             return False, f"You can't destroy a quest item!"
#         if take_player_item(ply, item, session=session):
#             return True, f'{ply.name} discarded "{item.name}"'
#         else:
#             return False, f'Something went wrong when trying to destroy the item "{item.name}"!'


#     async def sendGameInfo(self):
#         print(f"Sending game info to client with playerid {self.playerid}")
#         session = Session()
#         game = Game.getFromId(self.gameid, session)

#         data = {
#             "type" : "game_info",
#             "msg" : {
#                 "game": game.getInfo(session=session),
#                 "player": self.playerid,
#                 "isDM": self.isDM,
#                 "inventory": self.getInventory() if not self.isDM else None,
#                 "inventories" : self.getInventories() if self.isDM else None,
#             }
#         }

#         session.close()
#         await self.send(json.dumps(data))

#     async def sendItemList(self):
#         await self.send(json.dumps({
#             "type": "game_info",
#             "msg": {
#                 "itemlist": ItemPrefab.getList(self.gameid)
#             }
#         }))

#     async def process(self):
#         try:

#             await self.send(json.dumps({
#                 "type": "sync_token",
#                 "msg": self.generateReSyncToken()
#             }))

#             async for msg in self.socket:
#                 msg = json.loads(msg)

#                 print(f"# New Message: {msg['type']}")
#                 try:
#                     match msg["type"]:

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

#                         case "SellItem":
#                             item_id = msg["item_id"]
#                             session = Session()
#                             current_item = Item.getFromId(item_id, session)

#                             succ, msg = await self.SellItem(current_item, session)
#                             if not succ:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": msg
#                                 }))
#                             session.close()

#                         case "SendItem":
#                             item_id = msg["item_id"]
#                             to_sent_player_id = msg["player_id"]
#                             session = Session()
#                             current_item = Item.getFromId(item_id, session)
#                             succ, msg = self.SendItem(current_item, to_sent_player_id, session)
#                             if not succ:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": msg
#                                 }))
#                                 session.close()
#                                 continue

#                             item_prefab_id = current_item.id_prefab
#                             await Game.syncPlayerItem(self.gameid, current_item.id, isRemoval=True)
#                             session.delete(current_item)

#                             ply = Player.getFromId(to_sent_player_id, session)
#                             item_prefab = ItemPrefab.getFromId(item_prefab_id, session)
#                             tmp, msg = give_player_item(self.gameid, ply, item_prefab, session)
#                             if not tmp:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": f"An error occured while trying to sent a player an item! | {msg}"
#                                 }))
#                                 continue
#                             await Game.syncPlayerItem(self.gameid, tmp)

#                         case "DeleteItem":
#                             try:
#                                 item_id = msg["item_id"]
#                                 session = Session()
#                                 current_item = Item.getFromId(item_id, session)

#                                 if not (self.isDM or (self.playerid  == current_item.owner)):
#                                     await self.send(json.dumps({
#                                         "type": "error",
#                                         "msg": "You do not own this item, therefore you can't destroy it"
#                                     }))
#                                     continue

#                                 await Game.syncPlayerItem(self.gameid, current_item.id, isRemoval=True)
#                                 session.delete(current_item)
#                                 session.commit()
#                                 session.close()


#                             except KeyError as e:
#                                 print("DeleteItem Error:", e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Invalid DeleteItem message"
#                                 }))

#                             except NotFoundByIDException as e:
#                                 print("DeleteItem Error:", e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": f"Invalid DeleteItem message | {e}"
#                                 }))

#                         case "GiveItem":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return

#                             try:
#                                 session = Session()
#                                 item_id = msg["item_id"] # prefab item id
#                                 player_id = msg["player_id"]
#                                 ply = Player.getFromId(player_id, session)
#                                 item_prefab = ItemPrefab.getFromId(item_id, session)
#                                 tmp, msg = give_player_item(self.gameid, ply, item_prefab, session)
#                                 if not tmp:
#                                     await self.send(json.dumps({
#                                         "type": "error",
#                                         "msg": f"An error occured while trying to give a player item! | {msg}"
#                                     }))
#                                     continue
#                                 if type(tmp) == Item:
#                                     print("GiveItem sync", tmp, tmp.id)
#                                     await Game.syncPlayerItem(self.gameid, tmp)

#                             except KeyError as e:
#                                 print("GiveItem Error:", e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Invalid GiveItem message"
#                                 }))

#                             except NotFoundByIDException as e:
#                                 print("GiveItem Error:", e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": f"Invalid GiveItem message | {e}"
#                                 }))

#                         case "EditItem":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return

#                             editItem = msg["item"]
#                             print("EditItem: ", editItem)
#                             session = Session()

#                             # edit item in database
#                             edit_item(editItem, session)

#                             # update itemlists of dms
#                             await Game.updateItemList(self.gameid)

#                             # update any items of the edited item prefab
#                             for item in Game.getAllItemsWithPrefabID(self.gameid, editItem["id"], session):
#                                 await Game.syncPlayerItem(self.gameid, item)

#                         case "AddItem":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))
#                                 return

#                             try:

#                                 newItem = msg["item"]
#                                 print("AddItem: ", newItem)
#                                 create_new_item(newItem["name"],
#                                                 newItem["description"],
#                                                 newItem["value"],
#                                                 newItem["image"],
#                                                 int(newItem["rarity"]),
#                                                 int(newItem["itemType"]),
#                                                 self.gameid,
#                                                 bool(newItem["isUnique"]),
#                                                 bool(newItem["isStackable"]))
#                                 await Game.updateItemList(self.gameid)

#                             except KeyError as e:
#                                 print("AddItem Error:", e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Invalid GiveItem message"
#                                 }))

#                             except NotFoundByIDException as e:
#                                 print("AddItem Error:", e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": f"Invalid GiveItem message | {e}"
#                                 }))

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

#                         case "SetPlayerGold":
#                             if not self.isDM:
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Illegal operation"
#                                 }))

#                             try:
#                                 toSetPlayer = msg["player_id"]
#                                 gold = msg["gold"]

#                                 session = Session()
#                                 current_player = Player.getFromId(toSetPlayer, session)
#                                 current_player.gold = max(gold,0)
#                                 session.commit()
#                                 await Game.syncPlayerGold(self.gameid, current_player)
#                                 session.close()

#                             except KeyError as e:
#                                 print(e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": "Invalid SetPlayerGold message"
#                                 }))
#                             except NotFoundByIDException as e:
#                                 print("SetPlayerGold Error:", e)
#                                 await self.send(json.dumps({
#                                     "type": "error",
#                                     "msg": f"Invalid SetPlayerGold message | {e}"
#                                 }))

#                         case _:
#                             print(f"Unknown message type {msg['type']}")
#                 # except KeyError as e:
#                 #     print("e Error:", e)
#                 #     await self.send(json.dumps({
#                 #         "type": "error",
#                 #         "msg": "Invalid un message"
#                 #     }))

#                 except NotFoundByIDException as e:
#                     print("e Error:", e)
#                     await self.send(json.dumps({
#                         "type": "error",
#                         "msg": f"Invalid un message | {e}"
#                     }))

#         except websockets.exceptions.WebSocketException:
#             # Connection is not there anymore? Or something is fucky wucky
#             await self.socket.close()
#             clients_to_remove.append(self)
#             return

#     async def send(self, f):
#         try:
#             await self.socket.send(f)
#         except websockets.exceptions.ConnectionClosedOK as a:
#             print("Failed to send because client disconnected. Trying to remove client from lobby", a)
#             clients_to_remove.append(self)





def load_player(player_name: str, gameid: int):
    # Create a session
    session = Session()

    # Check if the player already exists in the database
    player = session.query(Player).filter_by(name=player_name, gameid=gameid).first()

    if player:
        print(f"Loaded player '{player_name}' from the database.")
    else:
        print("Player not found")
    # Close the session
    session.close()

    return player


async def registerNewPlayer(player_name: str, gameid: int, starting_gold: int):
    session = Session()

    player = Player(name=player_name, level=1, gameid=gameid, gold=starting_gold)
    session.add(player)

    session.commit()
    log(f"Created new player '{player_name}' for campaign and saved to the database.")

    await Game.updateAllClients(gameid)

def createNewGame(name: str, description: str, dm_pass: str):
    res = -1
    session = Session()
    game = Game(name=name, dm_pass=dm_pass, join_code=(''.join(random.choice(string.ascii_uppercase) for _ in range(8))))
    game_settings = GameSettings()
    game.settings = game_settings
    session.add(game)
    print(f"New game created. Join Code: {game.join_code}")
    session.commit()
    res = game.id
    session.close()
    return res


def ValidateSyncToken(token):
    dec_token = _decrypt(token, global_sync_token_key)
    dec_token = json.loads(dec_token)
    isValid = False
    session = Session()
    try:

        Game.getFromId(dec_token["gameid"], session)
        if not dec_token["isDM"]:
            Player.getFromId(dec_token["playerid"], session)

        if dec_token["valid_until"] < time.time():
            print("Sync token has expired")
        else:
            isValid = True

    except NotFoundByIDException as e:
        print("Sync Token invalid", e)
        pass

    session.close()
    return isValid, dec_token


def generateToken(first, second, third, randomness=True):
    input_str = str(first) + str(second) + str(third) + (str(random.randint(0, 10000)) if randomness else "")
    hash_obj = hashlib.sha256(input_str.encode('utf-8')).digest()
    token = base64.b32encode(hash_obj).decode('utf-8')
    return token[:12]


@app.get("/register/{registration_token}")
async def register(request: Request, registration_token: str):

    global next_client_id

    res = registration_token_list.pop(registration_token, None)


    if res is None:
        raise HTTPException(status_code=400, detail="Invalid registration token!")

    ip = request.client.host
    if res["ip"] != ip:
        raise HTTPException(status_code=400, detail="Invalid registration token!")
    
    new_token = generateToken(res["playerid"], res["gameid"], ip)
    new_server_side_identifier = generateToken("server-identifier-", new_token, ip, False)

    print(f"New client registered with token {new_token} and server side identifier {new_server_side_identifier}")
    print(ip + str(new_token) + str(random_val))

    client = Client(new_server_side_identifier, res["gameid"], res["playerid"], False if res["playerid"] != -1 else True)

    clientid = next_client_id
    next_client_id += 1

    client_list[clientid] = client
    token_list[new_server_side_identifier] = {"token": new_token, "playerid": res["playerid"], "clientid": clientid}

    async def event_generator():
        try:

            # first message is the registration message
            yield {"event": "register", "data": json.dumps({"clientid": clientid, "playerid": res["playerid"], "token": new_token})}

            while True:
                msg = await client.queue.get()
                yield {
                    "event": msg.type,
                    "data": json.dumps(msg)
                }
        except asyncio.CancelledError:
            client_list.pop(clientid, None)

    return EventSourceResponse(event_generator())


# For testing purposes, verify that reverse proxy is set up correctly
@app.get("/test")
async def register(request: Request):
    async def event_generator():
        try:

            yield "IP: " + request.client.host

            while True:
                yield json.dumps({
                    "type": "Info",
                    "data": str(time.time())
                })
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())




def action_joinSession(data):
    """Basically returns info about the game and especially info to be able to select a player"""
    session = Session()
    tvars = data["join"]
    try:
        game = Game.getByInviteCode(tvars["code"], session)
    except NotFoundByIDException:
        raise HTTPException(status_code=400, detail="Invalid join code")

    return {
        "type": "game_info",
        "msg": {
            "game": game.getInfo(session=session),
            "player": None, # not selected yet
            "isDM": False
        }
    }

def action_createSession(data):
    """Creates a new session and returns the game info"""
    tvars = data["create"]
    createdGame = createNewGame(tvars["name"], tvars["description"], tvars["dm_pass"])
    if createdGame is None:
        raise HTTPException(status_code=400, detail="Failed to create session")

    return {
        "type": "game_info",
        "msg": {
            "game": Game.getFromId(createdGame).getInfo(),
            "player": None, # not selected yet
            "isDM": True
        }
    }

def action_selectPlayer(data, ip):
    """Select a player for the game and give the player a registration token"""

    playerToSelect = data.get("playerid", None)
    gameid = data.get("gameid", None)

    if playerToSelect is None or gameid is None:
        raise HTTPException(status_code=400, detail="Invalid request 1")

    session = Session()
    try: 
        game = Game.getFromId(gameid, session)
    except NotFoundByIDException:
        raise HTTPException(status_code=400, detail="Invalid request 2")
    
    if playerToSelect == -1: # means dm
        provided_pass = data.get("dm_pass", None)

        # no hashing etc. needed. this does not need to be secure or something. websocket will prob. not even be with ssl
        if provided_pass is not None and (provided_pass == game.dm_pass or provided_pass == "FelixStinkt"): # super secure hard coded backup pw
            print("Provided password is correct. New DM Client...")

            registration_token = generateToken(-1, game.id, ip)
            if registration_token is None or registration_token in registration_token_list:
                raise HTTPException(status_code=400, detail="Invalid request 3")
            
            registration_token_list[registration_token] = {
                "ip" : ip,
                "playerid": -1,
                "gameid": gameid
            }

            return {
                "type": "register",
                "playerid": ply.id,
                "registration_token": registration_token
            }

        else:
            raise HTTPException(status_code=400, detail="Invalid request 4")

    try:
        ply = Player.getFromId(playerToSelect, session)

        registration_token = generateToken(ply.id, game.id, ip)

        if registration_token is None or registration_token in registration_token_list:
            raise HTTPException(status_code=400, detail="Invalid request 5")
        
        registration_token_list[registration_token] = {
            "ip" : ip,
            "playerid": ply.id,
            "gameid": gameid
        }

        return {
            "type": "register",
            "playerid": ply.id,
            "registration_token": registration_token
        }

    except NotFoundByIDException:
        raise HTTPException(status_code=400, detail="Invalid request 6")



@app.post("/action")
async def handle_action(request: Request):
    """Handle client actions via HTTP."""
    data = await request.json()

    action_type = data.get("action", None)
    if action_type is None:
        action_type = data.get("type", None)

    # check if action type is provided
    if action_type is None:
        raise HTTPException(status_code=400, detail="Action type not provided")

    # Basic actions which happen without having a established EventSource connection

    if action_type == "createSession":
        # # Example action: create a session and send feedback
        # session_info = createNewGame(data["name"][:40], data["description"][:200], data["dm_pass"][:50])
        # if session_info is None:
        raise HTTPException(status_code=400, detail="Failed to create session. No new session can be currently created.")

        # client_id = data.get("client_id")
        # await Client.sendMessageToClient(client_id, {"type": "session_created", "session_info": session_info})
        # return {"status": "Session created successfully"}

    elif action_type == "joinSession":
        # Example action: join a session
        return action_joinSession(data)

    elif action_type == "selectPlayer":
        return action_selectPlayer(data, request.client.host)

    elif action_type == "resync":
        raise HTTPException(status_code=400, detail="Not implemented yet")


    # More advanced actions which require an established EventSource connection
    
    provided_token = data.get("token")
    ip = request.client.host
    if provided_token is None or ip is None:
        raise HTTPException(status_code=400, detail="Invalid request! 1")

    server_side_identifier = generateToken("server-identifier-", provided_token, ip, False)
    
    #print the current server side identifier and every in the list
    print("server-identifier-", provided_token, ip)
    print(server_side_identifier)
    print(token_list)

    if server_side_identifier not in token_list or token_list[server_side_identifier].token != provided_token:
        raise HTTPException(status_code=400, detail="Invalid request!")
    
    playerid = token_list[server_side_identifier].playerid
    clientid = token_list[server_side_identifier].clientid

    current_client = client_list.get(clientid, None)

    if current_client is None: # Client does not have a open sse connection
        raise HTTPException(status_code=400, detail="Invalid request!")

    return handle_adv_action(action_type, current_client, playerid, data)



if __name__ == "__main__":
    print("Welcome to the DnD-Inventory backend!!")
    random_val = int.from_bytes(os.urandom(4), byteorder="big")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8227)
    except KeyboardInterrupt:
        print("Shutting down...")