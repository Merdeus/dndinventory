import React, { useEffect, useState } from 'react';
import { useWebSocket } from './WebSocketContext';
import {SelectGame} from './selectGame';
import { SelectPlayer } from './SelectPlayer';
import Inventory from './Inventory';
import { useMatch } from './MatchContext';
import TextInputModal from './TextInputModal';
import DungeonMasterView from './DungeonMasterView';

// PMIKUT

function Game() {

    const [isModalOpen, setIsModalOpen] = useState(false);
    const webSocketService = useWebSocket();
    const { matchState, updateMatchState, updateInventories, updateInventory } = useMatch();
    const [selectedPlayerID, setSelectedPlayerID ] = useState(-1);
    
    useEffect(() => {
  
      webSocketService.addCleanUpHandler({identifier: "Main_GameCleanup", callback: () => {
        console.log("Cleaning up");
        updateMatchState({
          isDM : false,
          player: null,
          game: null,
        });

        alert("Connection lost. You will need to rejoin the game.")
      }});

      const error_handlerMessage = {
        identifier: 'error_handler',
        messageType: 'error', 
        callback: (message) => {
          console.log("ERROR:", message.msg);
        }
      }
      webSocketService.addMessageHandler(error_handlerMessage);
  
      const gameinfo_handlerMessage = {
        identifier: 'global_info_handler',
        messageType: "game_info",
        callback: (message) => {
          console.log("game info:", message.msg);
          updateMatchState(message.msg);
        }
      }
      webSocketService.addMessageHandler(gameinfo_handlerMessage);

      const inventoryupdate_handlerMessage = {
        identifier: 'inventory_update_handler',
        messageType: "inventory_update",
        callback: (message) => {
          console.log("inventory_update:", message.msg);
          if (matchState.isDM) {
            if (matchState.inventories.hasOwnProperty(message.msg.playerid)) {
              console.log("Player exists on client. Updating inventory.")
              matchState.inventories[message.msg.playerid].inventory[message.msg.itemid] = message.msg.item;
            } else {
              console.log("Player does not exist on client. Aborting.")
              return;
            }
            updateMatchState([]);
          } else {
            updateInventory(message.msg.inventory);
          }
        }
      }
      webSocketService.addMessageHandler(inventoryupdate_handlerMessage);


      webSocketService.addMessageHandler({
        identifier: 'gold_update_handler',
        messageType: "gold_update",
        callback: (message) => {
          console.log("Gold Update:", message.msg);
          //matchState.game.players[message.msg.playerid].gold = message.msg.gold;
          matchState.inventories[message.msg.playerid].gold = message.msg.gold;
          updateMatchState([]); // stoopid
        }
      });

    });
  
    const players = [
      { name: 'Player 1' },
      { name: 'Player 2' },
      { name: 'Player 3' },
    ];
  
  
    const items = [
      { id: 1, name: 'Sword', description: 'A sharp blade', value: 150 },
      { id: 2, name: 'Shield', description: 'Protects you from attacks', value: 100 },
      { id: 3, name: 'Potion', description: 'Heals your wounds', value: 50 },
      { id: 4, name: 'Helmet', description: 'Protects your head', value: 75 },
      { id: 5, name: 'Shard', description: 'Reeeee', value: 75 },
      { id: 6, name: 'Excalibur', description: 'Very long text. Like verrrrrrry long. You know? Just to figure out if the given text bounds are fitting with the div container. Very important. Very much. Ogg. Ogg. Ogg. Oggg. Ogg. Very important. Very important.', value: 50 },
      { id: 7, name: 'Helmet', description: 'Protects your head', value: 75 },
      { id: 8, name: 'Shard', description: 'Reeeee', value: 175 },
      { id: 9, name: 'vHelmet', description: 'Protects your head', value: 75 },
      { id: 10, name: 'Shard', description: 'Reeeee', value: 75 },
      { id: 11, name: 'Helmet', description: 'Protects your head', value: 75 },
      { id: 12, name: 'Ultra Shard', description: 'Reeeee', value: 5 },
      { id: 13, name: 'Helmet', description: 'Protects your head', value: 75 },
      { id: 14, name: 'Shard', description: 'Reeeee', value: 75 },
   
    ];

    const playerSelected = (playerid) => {
      console.log("Selected player:", playerid)
      setSelectedPlayerID(playerid);
      if (playerid === -1) {
        console.log("Dungeon Master selected");
        handleOpenModal();
      } else {
        webSocketService.sendMessage({
          type: "selectPlayer", 
          playerid: playerid
        });
      }
    };

    const handleOpenModal = () => {
      setIsModalOpen(true);
    };
  
    const handleCloseModal = () => {
      setIsModalOpen(false);
    };
  
    const handleSubmitInput = (input) => {
      console.log("User input:", input);
      webSocketService.sendMessage({
        type: "selectPlayer", 
        playerid: selectedPlayerID,
        dm_pass: input
      });
    };
  
  
    if (!matchState.game) {
      return <SelectGame />;
    } else if (matchState.game && matchState.isDM) {
      return <DungeonMasterView />;
    } else if (matchState.game && !matchState.player) {
      return <>
              <SelectPlayer items={matchState.game.players} callback={playerSelected} />
              <TextInputModal
                isOpen={isModalOpen}
                onClose={handleCloseModal}
                onSubmit={handleSubmitInput}
              />
            </>;
    } else {
      return <Inventory items={items} players={players} />;
    }
  }
  
  export default Game;
  