// PlayerView.js
import React, { useState, useEffect } from 'react';
import Inventory from './Inventory';
import { useMatch } from './MatchContext';
import { useWebSocket } from './WebSocketContext';
import LootList from './LootList';
import './PlayerView.css';

const PlayerView = () => {
  const [showLootList, setShowLootList] = useState(false);
  const { matchState } = useMatch();
  const webSocketService = useWebSocket();

  const [playerInventory, setPlayerInventory] = useState([]);
  const lootList = matchState.loot.items || [];

  useEffect(() => {
  
    if (matchState.inventory) {
      setPlayerInventory(Object.values(matchState.inventory))
    }

  }, [matchState]);

  const sendItem = (playerID, itemID) => {
    console.log("Sending item to player: ", playerID);
    webSocketService.sendMessage({
      type: "SendItem",
      player_id: playerID,
      item_id: itemID
    });
  }

  const deleteItem = (itemID) => {
    console.log("Destroying item: ", itemID);
    webSocketService.sendMessage({
      type: "DeleteItem",
      item_id: itemID
    });
  }

  const sellItem = (itemID) => {
    console.log("Selling item: ", itemID);
    webSocketService.sendMessage({
      type: "SellItem",
      item_id: itemID
    });
  }


  return (
    <div className={`player-view-container ${showLootList ? 'show-loot-list' : ''}`}>
      <div className="player-view-inventory">
        <Inventory
          items={playerInventory}
          players={Object.values(matchState.game.players)}
          giveItem={sendItem}
          deleteItem={deleteItem}
          sellItem={sellItem}
        />
      </div>
      <div className="player-view-loot-list">
        {showLootList && <LootList items={matchState.loot.items} currentGold={matchState.loot.gold} />}
      </div>
    </div>
  );
};

export default PlayerView;
