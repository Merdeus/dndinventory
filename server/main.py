import itertools
import traceback
from typing import List, Type
from xmlrpc.client import Boolean
from dotenv import load_dotenv
from sqlalchemy.ext.hybrid import hybrid_property
import threading
import subprocess

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

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64

load_dotenv()

logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

engine = create_engine('sqlite:///players.db')
Base = sqlalchemy.orm.declarative_base()

enableDebugLog = True
printLogToConsole = True

sockets = []
games = {}
clientList = []
clients_to_remove = []

last_imports = {}

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

global_sync_token_key = os.getenv("SYNC_TOKEN_KEY")
if global_sync_token_key is None:
    global_sync_token_key = "NotReallySecure"

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

class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    log = Column(String)

class Player(Base):
    __tablename__ = 'players'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    level = Column(Integer)
    gold = Column(Integer)
    gameid = Column(Integer, ForeignKey('games.id'))
    game = relationship("Game", back_populates="players")

    def __repr__(self):
        return f"<Player(id={self.id}, name='{self.name}', level={self.level}, gold={self.gold}, game_id={self.gameid})>"

    @staticmethod
    def getFromId(tid : int, session):
        if session is None:
            raise NotFoundByIDException("Player.getFromId requires a session")
        ply = session.query(Player).filter_by(id=tid).first()
        if ply is None:
            raise NotFoundByIDException(f"Player {tid} not found")
        return ply


    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'level': self.level,
            'gold': self.gold,
            'game_id': self.game_id
        }

# items owned by a player
class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    id_prefab = Column(Integer, ForeignKey('item_prefabs.id'), nullable=False)
    count = Column(Integer, default=1)
    owner = Column(Integer, ForeignKey('players.id'))

    prefab = relationship("ItemPrefab", back_populates="items")

    @hybrid_property
    def type(self):
        return self.prefab.type

    @hybrid_property
    def name(self):
        return self.prefab.name

    @hybrid_property
    def rarity(self):
        return self.prefab.rarity

    @hybrid_property
    def description(self):
        return self.prefab.description

    @hybrid_property
    def value(self):
        return self.prefab.value

    @hybrid_property
    def img(self):
        return self.prefab.img


    def to_json(self):
        return {
            'id': self.id,
            'id_prefab': self.id_prefab,
            'name': self.name,
            'rarity': self.rarity,
            'description': self.description,
            'value': self.value,
            'img': self.img
            #'owner': self.owner
        }

    def isPlayerOwner(self, player):
        if type(player) == Player:
            return player.id == self.owner
        else:
            return player == self.owner

    def isQuestItem(self):
        return self.rarity == ItemRarity.QUEST_ITEM.value

    @staticmethod
    def getFromId(tid : int, session):
        if session is None:
            raise NotFoundByIDException("Item.getFromId requires a session")
        tmp = session.query(Item).filter_by(id=tid).first()
        if tmp is None:
            raise NotFoundByIDException("Item not found")
        else:
            return tmp


# items which can be given to players
class ItemPrefab(Base):
    __tablename__ = 'item_prefabs'

    # TODO: link a ItemPrefab to a game, important!

    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(Integer)
    rarity = Column(Integer)
    description = Column(String)
    value = Column(Integer)
    img = Column(String)
    gameid = Column(Integer, ForeignKey('games.id'))
    stackable = Column(Boolean, default=False)
    unique = Column(Boolean, default=False)

    items = relationship('Item', back_populates='prefab')

    @staticmethod
    def getFromId(tid : int, session):
        if session is None:
            raise NotFoundByIDException("game.getFromId requires a session")
        tmp = session.query(ItemPrefab).filter_by(id=tid).first()
        if tmp is None:
            raise NotFoundByIDException("No Item Prefab found with id {0}".format(tid))
        else:
            return tmp

    @staticmethod
    def getList(gameid : int):
        session = Session()
        tmp = session.query(ItemPrefab).filter_by(gameid=gameid).all()
        res = [
        {
            'id': i.id,
            'name': i.name,
            'rarity': i.rarity,
            'type': i.type,
            'description': i.description,
            'value': i.value,
            'img': i.img,
            'stackable': i.stackable,
            'unique': i.unique
        } for i in tmp]
        session.close()
        return res

class GameSettings(Base):
    __tablename__ = 'game_settings'

    id = Column(Integer, primary_key=True)
    gameid = Column(Integer, ForeignKey('games.id'), unique=True)
    game = relationship("Game", back_populates="settings")

    allowSelling = Column(Integer)

    shop_id = Column(Integer, ForeignKey('shops.id'))
    shop = relationship("Shop")

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


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    dm_pass = Column(String)
    join_code = Column(String)
    players = relationship("Player", back_populates="game")
    settings = relationship("GameSettings", uselist=False, back_populates="game")

    def getInfo(self, session=None):

        sessionNotGiven = session is None
        if sessionNotGiven:
            session = Session()

        tmp = session.query(Player).filter_by(gameid=self.id).all()

        t_players = {}
        for ply in tmp:
            t_players[ply.id] = {
                'id': ply.id,
                'name': ply.name,
                'gold': ply.gold,
            }

        data = {
            "game": {
                "id": self.id,
                "name": self.name,
                "join_code": self.join_code,
            },
            "players": t_players
        }

        if sessionNotGiven:
            session.close()

        return data

    @staticmethod
    def getFromId(tid : int, session):
        if session is None:
            raise NotFoundByIDException("game.getFromId requires a session")
        tmp = session.query(Game).filter_by(id=tid).first()
        if tmp is None:
            raise NotFoundByIDException("No game found with id {0}".format(tid))
        else:
            return tmp

    @staticmethod
    def getByInviteCode(invite_code: str, session):
        if session is None:
            raise NotFoundByIDException("game.getByInviteCode requires a session")
        tmp = session.query(Game).filter_by(join_code=invite_code).first()
        if tmp is None:
            raise NotFoundByIDException("No game found with invite code {0}".format(invite_code))
        else:
            return tmp

    @staticmethod
    async def updateAllClients(gameid):
        global clientList
        print(f"Updating all clients", clientList, len(clientList))
        for client in clientList:
            if client.gameid != gameid:
                continue
            print(f"Updating client for GameID {client.gameid}")
            await client.sendGameInfo()
        remove_disconnected_clients()

    @staticmethod
    async def updateItemList(gameid):
        global clientList
        print(f"Updating ItemList for all dm clients", clientList, len(clientList))
        for client in clientList:

            if not client.isDM:
                continue

            if client.gameid != gameid:
                continue

            await client.sendItemList()
        remove_disconnected_clients()

    @staticmethod
    async def syncPlayerGold(gameid : int, player : Player):
        global clientList
        print(f"Synchronising gold from player {player}")
        for client in clientList:
            if client.gameid != gameid:
                continue

            if client.isDM or client.playerid == player.id:
                data = {
                    "type": "gold_update",
                    "msg": {
                        "playerid": player.id,
                        "gold": player.gold
                    }
                }
                await client.send(json.dumps(data))
        remove_disconnected_clients()


    @staticmethod
    async def syncPlayerItem(gameid : int, item : (Item | int), isRemoval=False, isGlobal=False):

        session = Session()
        if type(item) == int:
            item = Item.getFromId(item, session)
        owner = item.owner

        global clientList
        print(f"Synchronising item {item} | isRemoval: {isRemoval} | isGlobal: {isGlobal}")
        for client in clientList:
            if client.gameid != gameid:
                continue

            if (client.isDM or client.playerid == owner) or isGlobal:

                if isRemoval:
                    data = {
                        "type": "item_removal",
                        "msg": {
                            "playerid": owner,
                            "itemid": item.id
                        }
                    }
                else:
                    if client.isDM:
                        data = {
                            "type": "inventory_update",
                            "msg": {
                                "playerid": owner,
                                "itemid": item.id,
                                "item" : {
                                    'id': item.id,
                                    'id_prefab': item.id_prefab,
                                    'name': item.name,
                                    'rarity': item.rarity,
                                    'type': item.type,
                                    'description': item.description,
                                    'count': item.count,
                                    'value': item.value,
                                    'img': item.img,
                                    'stackable': item.prefab.stackable,
                                    'unique': item.prefab.unique
                                }
                            }
                        }
                    else:
                        data = {
                            "type": "inventory_update",
                            "msg": {
                                "itemid": item.id,
                                "item": {
                                    'id': item.id,
                                    'id_prefab': item.id_prefab,
                                    'name': item.name,
                                    'rarity': item.rarity,
                                    'type': item.type,
                                    'description': item.description,
                                    'count': item.count,
                                    'value': item.value,
                                    'img': item.img,
                                    'stackable': item.prefab.stackable,
                                    'unique': item.prefab.unique
                                }
                            }
                        }
                await client.send(json.dumps(data))

        remove_disconnected_clients()

    @staticmethod
    def getAllItemsWithPrefabID(gameid : int, prefabID : int, session):
        if session is None:
            raise NotFoundByIDException("Game.getAllItemsWithPrefabID requires a session")
        return session.query(Item).filter_by(id_prefab=prefabID).all()


class Shop(Base):
    __tablename__ = 'shops'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(String)
    gold = Column(Integer)

    def __repr__(self):
        return f"<Shop(id={self.id}, name='{self.name}', location='{self.location}')>"

class ShopItem(Base):
    __tablename__ = 'shop_items'

    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, ForeignKey('shops.id'))
    item_id = Column(Integer, ForeignKey('items.id'))
    count = Column(Integer)

    shop = relationship("Shop")
    item = relationship("Item")

    def __repr__(self):
        return f"<ShopItem(id={self.id}, shop_id={self.shop_id}, item_id={self.item_id}, count={self.count})>"

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


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

class Client:
    def __init__(self, socket, gameid, playerid, isDM=False):
        self.socket = socket
        self.gameid = gameid
        self.playerid = playerid
        self.isDM = isDM

    def generateReSyncToken(self):
        token = json.dumps({
            "gameid": self.gameid,
            "playerid": self.playerid,
            "isDM": self.isDM,
            "valid_until": round(time.time() + 14400)
        })

        return _encrypt(token, global_sync_token_key)


    def getInventory(self):
        session = Session()
        items = session.query(Item).filter_by(owner=self.playerid).all()
        inventory = {}

        for i in items:
            inventory[i.id] = {
                'id': i.id,
                'id_prefab': i.id_prefab,
                'name': i.name,
                'rarity': i.rarity,
                'type': i.type,
                'description': i.description,
                'count': i.count,
                'value': i.value,
                'img': i.img,
                'stackable': i.prefab.stackable,
                'unique': i.prefab.unique
            }
        session.close()
        return inventory

    def getInventories(self):
        session = Session()

        try:
            current_game = Game.getFromId(self.gameid, session)

            # Retrieve all players associated with the current game
            players = session.query(Player).filter_by(gameid=current_game.id).all()

            # Initialize a dictionary to hold all inventories
            all_inventories = {}

            # For each player, retrieve their inventory
            for player in players:
                tmp = session.query(Item).filter_by(owner=player.id).all()
                inventory = {}
                for i in tmp:
                    inventory[i.id] = {
                        'id': i.id,
                        'id_prefab': i.id_prefab,
                        'name': i.name,
                        'rarity': i.rarity,
                        'type': i.type,
                        'description': i.description,
                        'count': i.count,
                        'value': i.value,
                        'img': i.img,
                        'stackable': i.prefab.stackable,
                        'unique': i.prefab.unique
                    }

                # Add the player's inventory to the all_inventories dictionary
                all_inventories[player.id] = {
                    'id': player.id,
                    'name': player.name,
                    'gold': player.gold,
                    'inventory': inventory
                }

            return all_inventories
        finally:
            session.close()

    def isAllowedToSell(self, item : Item) -> bool:
        if self.isDM:
            return False
        # TODO: Add check that global sell is active and item is not a questitem
        return True


    async def SellItem(self, item : Item, session) -> (bool, str):
        if self.isDM:
            return False, "You are a DM, you can't sell items... duh"
        if not item.isPlayerOwner(self.playerid):
            return False, f"You can't sell an item that is not owned by your player!"
        if item.isQuestItem():
            return False, f"You can't sell a quest item!"
        if not self.isAllowedToSell(item):
            return False, f"You currently are not able to sell anything."

        ply = Player.getFromId(self.playerid, session)

        ply.gold += item.value

        await Game.syncPlayerItem(self.gameid, item.id, isRemoval=True)
        session.delete(item)
        session.commit()
        await Game.syncPlayerGold(self.gameid, ply)

        message = f'Player {ply.name} sold item "{item.name}" for {item.value} gold'
        log(message)
        return True, message

    def SendItem(self, item : Item, toSentplayer : int, session) -> (bool, string):
        # maybe check if both players are part of the same game?
        if not self.isDM and not item.isPlayerOwner(self.playerid):
            return False, f"You don't own this item!"

        return True, ""


    def DestroyItem(self, item : int) -> (bool, str):

        session = Session()
        item = Item.getFromId(item)
        ply = Player.getFromId(self.playerid, session)
        if item is None:
            return False, f"This item does not exist!"

        if item.isQuestItem():
            return False, f"You can't destroy a quest item!"
        if take_player_item(ply, item, session=session):
            return True, f'{ply.name} discarded "{item.name}"'
        else:
            return False, f'Something went wrong when trying to destroy the item "{item.name}"!'


    async def sendGameInfo(self):
        print(f"Sending game info to client with playerid {self.playerid}")
        session = Session()
        game = Game.getFromId(self.gameid, session)

        data = {
            "type" : "game_info",
            "msg" : {
                "game": game.getInfo(session=session),
                "player": self.playerid,
                "isDM": self.isDM,
                "inventory": self.getInventory() if not self.isDM else None,
                "inventories" : self.getInventories() if self.isDM else None,
            }
        }

        session.close()
        await self.send(json.dumps(data))

    async def sendItemList(self):
        await self.send(json.dumps({
            "type": "game_info",
            "msg": {
                "itemlist": ItemPrefab.getList(self.gameid)
            }
        }))

    async def process(self):
        try:

            await self.send(json.dumps({
                "type": "sync_token",
                "msg": self.generateReSyncToken()
            }))

            async for msg in self.socket:
                msg = json.loads(msg)

                print(f"# New Message: {msg['type']}")
                try:
                    match msg["type"]:

                        case "ClaimLootItem":
                            print(f"CLAIMLOOTITEM {msg}")
                            loot_id = msg["loot_id"]
                            currentLootPool = LootPool.create_new_lootpool(self.gameid)
                            if currentLootPool.loot.get(loot_id) is None:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": f"Item {loot_id} does not exist!"
                                }))
                                continue
                            currentLootPool.setClaim(loot_id, self.playerid)
                            await currentLootPool.sendLootList()

                        case "VoteLootItem":

                            loot_id = msg["loot_id"]
                            player_id = msg["player_id"]
                            currentLootPool = LootPool.create_new_lootpool(self.gameid)
                            if currentLootPool.loot.get(loot_id) is None:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": f"Item {loot_id} does not exist!"
                                }))
                                continue
                            session = Session()
                            try:
                                target_player = Player.getFromId(player_id, session)
                                if target_player.gameid != self.gameid:
                                    await self.send(json.dumps({
                                        "type": "error",
                                        "msg": f"Invalid VoteLootitem!"
                                    }))
                                    return
                                currentLootPool.setVote(loot_id, self.playerid, player_id)
                                await currentLootPool.sendLootList()
                            except NotFoundByIDException:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": f"Invalid VoteLootitem!"
                                }))
                                continue
                            finally:
                                session.close()

                        case "LootPhaseDone":
                            currentLootPool = LootPool.create_new_lootpool(self.gameid)
                            if currentLootPool.phase != LootPool.Phase.CLAIM and currentLootPool.phase != LootPool.Phase.VOTE:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Invalid request"
                                }))
                                continue

                            if currentLootPool.handleNewFinish(self.playerid):
                                currentLootPool.nextPhase()

                            await currentLootPool.sendLootList()

                        case "AddLootItem":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            item_id = msg["item_id"]
                            currentLootPool = LootPool.create_new_lootpool(self.gameid)

                            if currentLootPool.phase.value != 0:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "You can only add loot during the preparations."
                                }))
                                continue

                            currentLootPool.addLoot(item_id)
                            await currentLootPool.sendLootList()

                        case "RemoveLootItem":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            loot_id = msg["loot_id"]
                            currentLootPool = LootPool.create_new_lootpool(self.gameid)
                            currentLootPool.removeLoot(loot_id)
                            await currentLootPool.sendLootList()

                        case "GenerateLootItems":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            countList = msg["count_list"]
                            currentLootPool = LootPool.create_new_lootpool(self.gameid)
                            currentLootPool.generateRandomLoot(countList)
                            await currentLootPool.sendLootList()

                        case "SetLootGold":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return
                            currentLootPool = LootPool.create_new_lootpool(self.gameid)
                            currentLootPool.gold = msg["loot_gold"]
                            await currentLootPool.sendLootList()


                        case "ClearLoot":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return
                            LootPool.delete_by_gameid(self.gameid)
                            currentLootPool = LootPool.create_new_lootpool(self.gameid)
                            await currentLootPool.sendLootList()

                        case "DistributeLoot":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            currentLootPool = LootPool.find_by_gameid(self.gameid)
                            if currentLootPool is None:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "There is no active lootpool"
                                }))
                                continue

                            selected_players = msg["players"]
                            if len(selected_players) < 1:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "You have to select more than one player"
                                }))
                                continue

                            if len(currentLootPool.loot) < 1:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "You have to add loot to distribute"
                                }))
                                continue

                            session = Session()
                            try:
                                for player in selected_players:
                                    Player.getFromId(player, session)
                            except NotFoundByIDException:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Invalid player in player selection"
                                }))
                                continue

                            currentLootPool.players = [int(i) for i in selected_players]
                            currentLootPool.nextPhase()
                            await currentLootPool.sendLootList()
                            session.close()

                        case "SellItem":
                            item_id = msg["item_id"]
                            session = Session()
                            current_item = Item.getFromId(item_id, session)

                            succ, msg = await self.SellItem(current_item, session)
                            if not succ:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": msg
                                }))
                            session.close()

                        case "SendItem":
                            item_id = msg["item_id"]
                            to_sent_player_id = msg["player_id"]
                            session = Session()
                            current_item = Item.getFromId(item_id, session)
                            succ, msg = self.SendItem(current_item, to_sent_player_id, session)
                            if not succ:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": msg
                                }))
                                session.close()
                                continue

                            item_prefab_id = current_item.id_prefab
                            await Game.syncPlayerItem(self.gameid, current_item.id, isRemoval=True)
                            session.delete(current_item)

                            ply = Player.getFromId(to_sent_player_id, session)
                            item_prefab = ItemPrefab.getFromId(item_prefab_id, session)
                            tmp, msg = give_player_item(self.gameid, ply, item_prefab, session)
                            if not tmp:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": f"An error occured while trying to sent a player an item! | {msg}"
                                }))
                                continue
                            await Game.syncPlayerItem(self.gameid, tmp)

                        case "DeleteItem":
                            try:
                                item_id = msg["item_id"]
                                session = Session()
                                current_item = Item.getFromId(item_id, session)

                                if not (self.isDM or (self.playerid  == current_item.owner)):
                                    await self.send(json.dumps({
                                        "type": "error",
                                        "msg": "You do not own this item, therefore you can't destroy it"
                                    }))
                                    continue

                                await Game.syncPlayerItem(self.gameid, current_item.id, isRemoval=True)
                                session.delete(current_item)
                                session.commit()
                                session.close()


                            except KeyError as e:
                                print("DeleteItem Error:", e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Invalid DeleteItem message"
                                }))

                            except NotFoundByIDException as e:
                                print("DeleteItem Error:", e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": f"Invalid DeleteItem message | {e}"
                                }))

                        case "GiveItem":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            try:
                                session = Session()
                                item_id = msg["item_id"] # prefab item id
                                player_id = msg["player_id"]
                                ply = Player.getFromId(player_id, session)
                                item_prefab = ItemPrefab.getFromId(item_id, session)
                                tmp, msg = give_player_item(self.gameid, ply, item_prefab, session)
                                if not tmp:
                                    await self.send(json.dumps({
                                        "type": "error",
                                        "msg": f"An error occured while trying to give a player item! | {msg}"
                                    }))
                                    continue
                                if type(tmp) == Item:
                                    print("GiveItem sync", tmp, tmp.id)
                                    await Game.syncPlayerItem(self.gameid, tmp)

                            except KeyError as e:
                                print("GiveItem Error:", e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Invalid GiveItem message"
                                }))

                            except NotFoundByIDException as e:
                                print("GiveItem Error:", e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": f"Invalid GiveItem message | {e}"
                                }))

                        case "EditItem":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            editItem = msg["item"]
                            print("EditItem: ", editItem)
                            session = Session()

                            # edit item in database
                            edit_item(editItem, session)

                            # update itemlists of dms
                            await Game.updateItemList(self.gameid)

                            # update any items of the edited item prefab
                            for item in Game.getAllItemsWithPrefabID(self.gameid, editItem["id"], session):
                                await Game.syncPlayerItem(self.gameid, item)

                        case "AddItem":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            try:

                                newItem = msg["item"]
                                print("AddItem: ", newItem)
                                create_new_item(newItem["name"],
                                                newItem["description"],
                                                newItem["value"],
                                                newItem["image"],
                                                int(newItem["rarity"]),
                                                int(newItem["itemType"]),
                                                self.gameid,
                                                bool(newItem["isUnique"]),
                                                bool(newItem["isStackable"]))
                                await Game.updateItemList(self.gameid)

                            except KeyError as e:
                                print("AddItem Error:", e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Invalid GiveItem message"
                                }))

                            except NotFoundByIDException as e:
                                print("AddItem Error:", e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": f"Invalid GiveItem message | {e}"
                                }))

                        case "ImportNewItems":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            # cooldown
                            global last_imports
                            print("ImportNewItems: ", last_imports, self.socket.remote_address[0] in last_imports)
                            if self.socket.remote_address[0] in last_imports:
                                if last_imports[self.socket.remote_address[0]] > (time.time() - 600):
                                    await self.send(json.dumps({
                                        "type": "error",
                                        "msg": "Import cooldown. Chill!"
                                    }))
                                    await self.send(json.dumps({
                                        "type": "items_imported",
                                        "success": False
                                    }))
                                    continue
                            last_imports[self.socket.remote_address[0]] = time.time()

                            # ignore which kind of items you actually want to import because there currently is only dnd items
                            try:
                                threading.Thread(target=run_import_script, args=(self.gameid, self.send)).start()

                            except KeyError as e:
                                print("ImportNewItems Error:", e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Invalid ImportNewItems message"
                                }))

                        case "CreatePlayer":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return
                            try:
                                print(msg)
                                player_name = msg["player_name"]
                                player_gold = msg["gold"]
                                if player_name is None or player_name == "" or player_gold is None:
                                    raise KeyError

                                player_gold = max(0, player_gold)
                                await registerNewPlayer(player_name, self.gameid, player_gold)
                            except KeyError as e:
                                print(e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Invalid CreatePlayer message"
                                }))

                        case "SetPlayerGold":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))

                            try:
                                toSetPlayer = msg["player_id"]
                                gold = msg["gold"]

                                session = Session()
                                current_player = Player.getFromId(toSetPlayer, session)
                                current_player.gold = max(gold,0)
                                session.commit()
                                await Game.syncPlayerGold(self.gameid, current_player)
                                session.close()

                            except KeyError as e:
                                print(e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Invalid SetPlayerGold message"
                                }))
                            except NotFoundByIDException as e:
                                print("SetPlayerGold Error:", e)
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": f"Invalid SetPlayerGold message | {e}"
                                }))

                        case _:
                            print(f"Unknown message type {msg['type']}")
                # except KeyError as e:
                #     print("e Error:", e)
                #     await self.send(json.dumps({
                #         "type": "error",
                #         "msg": "Invalid un message"
                #     }))

                except NotFoundByIDException as e:
                    print("e Error:", e)
                    await self.send(json.dumps({
                        "type": "error",
                        "msg": f"Invalid un message | {e}"
                    }))

        except websockets.exceptions.WebSocketException:
            # Connection is not there anymore? Or something is fucky wucky
            await self.socket.close()
            clients_to_remove.append(self)
            return

    async def send(self, f):
        try:
            await self.socket.send(f)
        except websockets.exceptions.ConnectionClosedOK as a:
            print("Failed to send because client disconnected. Trying to remove client from lobby", a)
            clients_to_remove.append(self)



def log(msg : str, session=Session(), level=LogLevel.INFO) -> None:

    if level == LogLevel.DEBUG and not enableDebugLog:
        return

    toAdd = loglevel_prefixes.get(level, "[?]") + " " + msg
    if printLogToConsole or level == LogLevel.ERROR:
        print(toAdd)
    session.add(History(log=toAdd))
    session.commit()
    session.close()


def logErrorAndNotify(msg : str) -> None:
    log(msg, level=LogLevel.ERROR)
    # TODO: notify dm
    pass

def syncPlayer(player) -> None:
    # Loop through active connections and if one is with this player send him an update
    # additionally give dm sync of this player
    pass

def give_player_item(gameid, player, item : ItemPrefab, session = None) -> (Item | bool, str | None):
    if player is None or item is None:
        logErrorAndNotify("Player or item is None. Aborting giving player a item.")
        return False, "Malformed Request"

    notSession = session is None
    if notSession:
        session = Session()

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

    if notSession:
        session.close()
        return True, "Player received Item succesfully"
    return newItem or curItem, "Player received Item succesfully"


def take_player_item(player, item : Item, session = None) -> bool:
    notSession = session is None
    if notSession:
        session = Session()

    if player is None or item is None:
        logErrorAndNotify("Player or item is None. Aborting taking item from player.")
        return False

    if item.owner != player.id:
        logErrorAndNotify("Given player does not own this item, therefore this item cannot be removed.")
        return False

    log(f"Player {player.name} [ID: {player.id}] has lost item {item.name} [ID: {item.id}]")

    session.delete(item)
    session.commit()

    if notSession:
        session.close()

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


def create_new_item(name : str, description: str, value : int, img : str, rarity: int, itype: int, gameid : int, unique : bool = False, stackable : bool = False) -> bool:
    if name is None or description is None or value is None:
        return False

    session = Session()
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
    log(f"Item {name} [ID: {name}] has been created", session=session)
    session.close()
    return True

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


def parse_register_msg(msg):
    j = json.loads(msg)
    if j["type"] != "register":
        print("Not a registration message")
        return None
    return j

async def newserver(websocket, path):
    # wait for registration message
    global clientList
    print("New websocket connection...")
    try:
        registerMsg = parse_register_msg(await websocket.recv())
        match registerMsg["action"]:
            case "resync":
                token = registerMsg["sync_token"]
                isValid, token = ValidateSyncToken(token)
                if not isValid:
                    error = {
                        "type": "error",
                        "msg": "Invalid sync token. You have to join manually"
                    }
                    await websocket.send(json.dumps(error))

                newClient = Client(websocket, token["gameid"], None if token["isDM"] else token["playerid"], token["isDM"])
                clientList.append(newClient)
                await newClient.sendGameInfo()
                if token["isDM"]:
                    await newClient.sendItemList()
                currentLootPool = LootPool.create_new_lootpool(token["gameid"])
                await currentLootPool.sendLootList()
                await newClient.process()

            case "createSession":
                tvars = registerMsg["create"]
                print(tvars, tvars["name"], tvars["description"], tvars["dm_pass"])
                createdGame = createNewGame(tvars["name"], tvars["description"], tvars["dm_pass"])
                if createdGame is None:
                    error = {
                        "type": "error",
                        "msg": "Invalid registration message"
                    }
                    await websocket.send(json.dumps(error))
                    return

                newClient = Client(websocket, createdGame, None, True)
                clientList.append(newClient)
                await newClient.sendGameInfo()
                await newClient.sendItemList()
                await newClient.process()

            case "joinSession":
                session = Session()
                tvars = registerMsg["join"]
                try:
                    game = Game.getByInviteCode(tvars["code"], session)
                except NotFoundByIDException:
                    session.close()
                    error = {
                        "type": "error",
                        "msg": "Invalid join code"
                    }
                    await websocket.send(json.dumps(error))
                    return
                except (KeyError | TypeError):
                    session.close()
                    return

                playerSelected = False
                while playerSelected is False:
                    await websocket.send(json.dumps(
                        {
                            "type": "game_info",
                            "msg": {
                                "game": game.getInfo(session=session),
                                "player": None, # not selected yet
                                "isDM": False
                            }
                        }))
                    msg = json.loads(await websocket.recv())
                    if msg["type"] == "selectPlayer":
                        playerToSelect = msg["playerid"]

                        if playerToSelect == -1: # means dm
                            provided_pass = msg["dm_pass"]

                            # no hashing etc. needed. this does not need to be secure or something. websocket will prob. not even be with ssl
                            if provided_pass is not None and (provided_pass == game.dm_pass or provided_pass == "FelixStinkt"): # super secure hard coded backup pw
                                print("Provided password is correct. New DM Client...")
                                newClient = Client(websocket, game.id, None, True)
                                clientList.append(newClient)
                                await newClient.sendGameInfo()
                                await newClient.sendItemList()
                                currentLootPool = LootPool.create_new_lootpool(game.id)
                                await currentLootPool.sendLootList()
                                await newClient.process()
                                return
                            else:
                                print("Provided dm pass is incorrect")
                                session.close()
                                error = {
                                    "type": "error",
                                    "msg": "Invalid dm password"
                                }
                                await websocket.send(json.dumps(error))
                                return

                        try:
                            session = Session()
                            ply = Player.getFromId(playerToSelect, session)
                            newClient = Client(websocket, game.id, ply.id, False)
                            clientList.append(newClient)
                            session.close()
                            await newClient.sendGameInfo()
                            currentLootPool = LootPool.create_new_lootpool(game.id)
                            await currentLootPool.sendLootList()
                            await newClient.process()
                            return
                        except NotFoundByIDException:
                            error = {
                                "type": "error",
                                "msg": "Invalid player selected"
                            }
                            await websocket.send(json.dumps(error))

        return

    except KeyError as e:
        print(e)
        error = {
            "type": "error",
            "msg": "Invalid registration message"
        }
        await websocket.send(json.dumps(error))
        return

    except websockets.exceptions.WebSocketException:
        print("Websocket connection broken")
        await websocket.close()
        return

    # except Exception as e:
    #     error = {
    #         "type": "error",
    #         "msg": f"If you see this error something weird just happened and you will have to reconnect. [{e}]"
    #     }
    #     await websocket.send(json.dumps(error))
    #     return






# only start if main is the one that is executed
if __name__ == "__main__":
    print("Welcome to the DnD-Inventory backend!!")

    certificate_path = os.getenv("SSL_CERTIFICATE")
    privatekey_path = os.getenv("SSL_PRIVATE_KEY")

    ssl_context = None

    if certificate_path is not None and privatekey_path is not None:
        # creating ssl context for secure connection (wss instead of ws)
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(certfile=certificate_path, keyfile=privatekey_path)
        except FileNotFoundError:
            ssl_context = None
            print("Certificate file not found")
    else:
        print("No SSL certificate provided")

    # create websocket server
    start_server = websockets.serve(newserver, '0.0.0.0', 8273, ping_interval=None, ssl=ssl_context)
    asyncio.get_event_loop().run_until_complete(start_server)

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("Shutting down...")