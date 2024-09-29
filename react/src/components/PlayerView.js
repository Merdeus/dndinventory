import React, { useState, useEffect } from 'react';
import Inventory from './Inventory';
import { useMatch } from './MatchContext';
import { useSSE } from './SSEContext';
import LootList from './LootList';
import './PlayerView.css';

const PlayerView = () => {
  const [showLootList, setShowLootList] = useState(false);
  const { matchState } = useMatch();
  const webSocketService = useSSE();

  const [playerInventory, setPlayerInventory] = useState([]);
  const lootList = matchState.loot.items || [];

  useEffect(() => {
    if (matchState.inventory) {
      setPlayerInventory(Object.values(matchState.inventory));
    }

    if (matchState.loot && matchState.loot.phase && (matchState.loot.phase === 1 || matchState.loot.phase === 2)) {
      setShowLootList(true);
    } else {
      setShowLootList(false);
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

  //         <button className="top-bar-button">Button</button>

  return (
    <div className="player-view-wrapper">
      <div className="top-bar">
        <div className="player-info">
          <span className="player-name">Name: {matchState.player ? matchState.game.players[matchState.player].name : 'Unknown Player'}</span>
          <span className="player-gold">Gold: {matchState.player ? matchState.game.players[matchState.player].gold : 0}GP</span>
        </div>

      </div>
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
          {showLootList && <LootList items={Object.values(matchState.loot.items)} currentGold={matchState.loot.gold} />}
        </div>
      </div>
    </div>
  );
};

export default PlayerView;
