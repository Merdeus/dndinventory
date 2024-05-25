import itertools
import traceback
from typing import List, Type
from xmlrpc.client import Boolean
from dotenv import load_dotenv

print("Welcome to the DnD-Inventory backend!!")

import json
import uuid
import asyncio
import datetime
import random
import websockets
import string
import ssl
import os
import websockets.exceptions

import logging
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

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
    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    VERY_RARE = 4
    LEGENDARY = 5
    QUEST_ITEM = 6

item_rarity_names = {
    ItemRarity.COMMON: "Common",
    ItemRarity.UNCOMMON: "Uncommon",
    ItemRarity.RARE: "Rare",
    ItemRarity.VERY_RARE: "Very Rare",
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

item_type_names = {
    ItemType.WEAPON: "Weapon",
    ItemType.ARMOR: "Armor",
    ItemType.ADVENTURE_GEAR: "Adventure Gear",
    ItemType.TOOL: "Tool",
    ItemType.CONSUMABLE: "Consumable",
    ItemType.MAGICAL_ITEM: "Magical Item",
    ItemType.VALUABLE: "Valuable",
}


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
    id_prefab = Column(Integer)
    type = Column(Integer)
    name = Column(String)
    rarity = Column(Integer)
    description = Column(String)
    value = Column(Integer)
    img = Column(String)
    count = Column(Integer)
    amount = Column(Integer)
    owner = Column(Integer, ForeignKey('players.id'))

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
        return self.rarity == ItemRarity.QUEST_ITEM

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
    def getList():
        session = Session()
        tmp = session.query(ItemPrefab).all()
        res = [
        {
            'id': i.id,
            'name': i.name,
            'rarity': i.rarity,
            'description': i.description,
            'value': i.value,
            'img': i.img
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


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    dm_pass = Column(String)
    join_code = Column(String)

    settings = relationship("GameSettings", uselist=False, back_populates="game")


    def getInfo(self, session=None):

        sessionNotGiven = session is None
        if sessionNotGiven:
            session = Session()

        tmp = session.query(Player).filter_by(gameid=self.id).all()

        data = {
            "game": {
                "id": self.id,
                "name": self.name,
                "join_code": self.join_code,
            },
            "players": [{
                'id': i.id,
                'name': i.name,
                'gold': i.gold,
            } for i in tmp]
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
                                    'description': item.description,
                                    'value': item.value,
                                    'img': item.img
                                }
                            }
                        }
                    else:
                        data = {
                            "type": "inventory_update",
                            "msg": {
                                "inventory": {
                                    item.id : {
                                        'id': item.id,
                                        'id_prefab': item.id_prefab,
                                        'name': item.name,
                                        'rarity': item.rarity,
                                        'description': item.description,
                                        'value': item.value,
                                        'img': item.img
                                    }
                                }
                            }
                        }
                await client.send(json.dumps(data))

        remove_disconnected_clients()


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

class Client:
    def __init__(self, socket, gameid, playerid, isDM=False):
        self.socket = socket
        self.gameid = gameid
        self.playerid = playerid
        self.isDM = isDM


    def getInventory(self):
        session = Session()
        tmp = session.query(Item).filter_by(owner=self.playerid).all()
        res = [{
            'id': i.id,
            'id_prefab': i.id_prefab,
            'name': i.name,
            'rarity': i.rarity,
            'description': i.description,
            'value': i.value,
            'img': i.img
        } for i in tmp]
        session.close()
        return res

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
                        'description': i.description,
                        'value': i.value,
                        'img': i.img
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

        message = f'Player {ply.name} sold item "{item.name}" for {item.value} gold'
        log(message)
        return True, message

    def SendItem(self, item : Item, toSentplayer : int, session) -> (bool, str):
        # maybe check if both players are part of the same game?
        if not self.isDM and not item.isPlayerOwner(self.playerid):
            return False, f"You don't own this item!"

        item.owner = toSentplayer
        session.commit()

        return True


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
                "itemlist": ItemPrefab.getList()
            }
        }))

    async def process(self):
        try:
            async for msg in self.socket:
                msg = json.loads(msg)

                print(f"# New Message: {msg['type']}")
                try:
                    match msg["type"]:
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
                            await self.SendItem(current_item, to_sent_player_id, session)

                        case "DeleteItem":

                            try:
                                item_id = msg["item_id"]
                                player_id = msg["player_id"]
                                session = Session()
                                current_item = Item.getFromId(item_id, session)

                                if not (self.isDM or (player_id == self.playerid and player_id == current_item.owner)):
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
                                tmp = give_player_item(ply, item_prefab, session)
                                if not tmp:
                                    await self.send(json.dumps({
                                        "type": "error",
                                        "msg": "An error occured while trying to give a player item!"
                                    }))
                                    continue
                                if type(tmp) == Item:
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

                        case "AddItem":
                            if not self.isDM:
                                await self.send(json.dumps({
                                    "type": "error",
                                    "msg": "Illegal operation"
                                }))
                                return

                            try:

                                newItem = msg["item"]
                                create_new_item(newItem["name"], newItem["description"], newItem["value"], newItem["image"], int(newItem["rarity"]), int(newItem["itemType"]))
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
                except KeyError as e:
                    print("e Error:", e)
                    await self.send(json.dumps({
                        "type": "error",
                        "msg": "Invalid un message"
                    }))

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

def give_player_item(player, item : ItemPrefab, session = None) -> Item | bool:
    if player is None or item is None:
        logErrorAndNotify("Player or item is None. Aborting giving player a item.")
        return False

    notSession = session is None
    if notSession:
        session = Session()

    curItem = session.query(Item).filter_by(id_prefab=item.id, owner=player.id).first()
    newItem = None
    if curItem is None:
        newItem = Item(
            id_prefab = item.id,
            type = item.type,
            name = item.name,
            rarity = item.rarity,
            description = item.description,
            value = item.value,
            img = item.img,
            count = 1,
            owner = player.id
        )
        session.add(newItem)
    else:
        curItem.count += 1
    session.commit()

    if notSession:
        session.close()
        return True
    return curItem or newItem


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

def create_new_item(name : str, description: str, value : int, img : str, rarity: int, itype: int) -> bool:
    if name is None or description is None or value is None:
        return False

    session = Session()
    session.add(ItemPrefab(
        name=name,
        description=description,
        value=value,
        rarity=rarity,
        type=itype,
        img=img,
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
    game = Game(name=name, dm_pass=dm_pass, join_code=(''.join(random.choice(string.ascii_uppercase) for _ in range(6))))
    game_settings = GameSettings()
    game.settings = game_settings
    session.add(game)
    print(f"New game created. Join Code: {game.join_code}")
    session.commit()
    res = game.id
    session.close()
    return res

def joinGame():
    pass

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
                            ply = Player.getFromId(playerToSelect)
                            newClient = Client(websocket, game.id, ply.id, False)
                            clientList.append(newClient)
                            await newClient.sendGameInfo()
                            await newClient.process()
                            return
                        except NotFoundByIDException:
                            error = {
                                "type": "error",
                                "msg": "Invalid player selected"
                            }
                            await websocket.send(json.dumps(error))

        return

    except KeyError:
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



certificate_path = os.getenv("SSL_CERTIFICATE")
privatekey_path = os.getenv("SSL_PRIVATE_KEY")

ssl_context = None

if certificate_path is not None and privatekey_path is not None:
    # creating ssl context for secure connection (wss instead of ws)
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
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