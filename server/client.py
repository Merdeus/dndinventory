from util import clientList, global_sync_token_key, _encrypt
from objects import *
import asyncio
import json
import time


class Client:
    def __init__(self, identifier, gameid, playerid, isDM=False):
        self.identifier = identifier
        self.playerid = playerid
        self.queue = asyncio.Queue()
        self.gameid = gameid
        self.isDM = isDM

    def generateReSyncToken(self):
        token = json.dumps({
            "gameid": self.gameid,
            "playerid": self.playerid,
            "isDM": self.isDM,
            "valid_until": round(time.time() + 28800)
        })
        return _encrypt(token, global_sync_token_key)
    

    def getInventory(self, session):
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
        return inventory



    def getInventories(self, session):

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
    
    def isAllowedToSell(self, item : Item, session) -> bool:
        if self.isDM:
            return False
        current_game = Game.getFromId(self.gameid, session)
        return current_game.sellingAllowed

    async def sendGameSync(self, session):
        print(f"Sending game sync to client with playerid {self.playerid}")
        game = Game.getFromId(self.gameid, session)

        await self.send({
            "type" : "game_info",
            "msg" : {
                "game": game.getInfo(session=session),
                "player": self.playerid,
                "isDM": self.isDM,
                "inventory": self.getInventory(session) if not self.isDM else None,
                "inventories" : self.getInventories(session) if self.isDM else None,
            }
        })

        if self.isDM:
            await self.send({
                "type": "game_info",
                "msg": {
                    "itemlist": ItemPrefab.getList(self.gameid, session)
                }
            })

    async def sendItemList(self, session):
        if self.isDM:
            await self.send({
                "type": "game_info",
                "msg": {
                    "itemlist": ItemPrefab.getList(self.gameid, session)
                }
            })

    async def send(self, message):
        await self.queue.put(message)

    @staticmethod
    async def sendMessageToClient(identifier, msg):
        if identifier in clientList:
            client = clientList[identifier]
            await client.send(msg)
        else:
            print(f"Client {identifier} not found")


async def sendMessageToPlayer(playerid, msg):
    # loop through client list and send message to every client with corresponding playerid
    for _, client in client_list.items():
        if client.playerid == playerid:
            await client.send(msg)