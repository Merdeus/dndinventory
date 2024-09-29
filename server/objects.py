import sqlalchemy
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from util import ItemRarity, client_list


from util import NotFoundByIDException, remove_disconnected_clients, clientList
import json

engine = create_engine('sqlite:///players.db')
Base = sqlalchemy.orm.declarative_base()

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
    def getList(gameid : int, session):
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
    players = relationship("Player", back_populates="game")
    settings = relationship("GameSettings", uselist=False, back_populates="game")

    sellingAllowed = False

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
                "sellingAllowed": self.sellingAllowed
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
        global client_list
        print(f"Updating all clients", len(client_list))
        for _, client in client_list.items():
            if client.gameid != gameid:
                continue
            print(f"Updating client for GameID {client.gameid}")
            await client.sendGameInfo()
        remove_disconnected_clients()

    @staticmethod
    async def updateItemList(gameid, session):
        global client_list
        print(f"Updating ItemList for all dm clients", len(client_list))
        for _, client in client_list.items():

            if not client.isDM:
                continue

            if client.gameid != gameid:
                continue

            await client.sendItemList(session)

    @staticmethod
    async def syncPlayerGold(gameid : int, player : Player):
        global client_list
        print(f"Synchronising gold from player {player}")
        for _, client in client_list.items():
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
                await client.send(data)

    @staticmethod
    async def syncPlayerItem(gameid : int, item : (Item | int), isRemoval=False, isGlobal=False):

        with Session() as session:
            if type(item) == int:
                item = Item.getFromId(item, session)
            owner = item.owner

            global client_list
            print(f"Synchronising item {item} | isRemoval: {isRemoval} | isGlobal: {isGlobal}")
            for _, client in client_list.items():
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
                    await client.send(data)


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