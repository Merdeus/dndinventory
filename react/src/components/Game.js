import React, { useEffect, useState } from 'react';
import { useSSE } from './SSEContext';
import {SelectGame} from './selectGame';
import { SelectPlayer } from './SelectPlayer';
import Inventory from './Inventory';
import { useMatch } from './MatchContext';
import TextInputModal from './TextInputModal';
import DungeonMasterView from './DungeonMasterView';
import PlayerView from './PlayerView';
import "./Game.css";

function Game() {

    const [isModalOpen, setIsModalOpen] = useState(false);
    const webSocketService = useSSE();
    const { matchState, updateMatchState, updateInventories, updateInventory } = useMatch();
    const [selectedPlayerID, setSelectedPlayerID ] = useState(-1);
    const [showReconnect, setShowReconnect] = useState(false);
    const [retryConnecting, setRetryConnecting] = useState(false);
    const [retryCount, setRetryCount] = useState(0);
    
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

      const registration_handlerMessage = {
        identifier: 'registration_handler',
        messageType: "register",
        callback: (message) => {
          console.log("registration token received:", message.msg);
          webSocketService.registration_token = message.registration_token;

          webSocketService.connect();

        }
      }
      webSocketService.addMessageHandler(registration_handlerMessage);

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
            matchState.inventory[message.msg.itemid] = message.msg.item;
            updateMatchState([]);
          }
        }
      }
      webSocketService.addMessageHandler(inventoryupdate_handlerMessage);

      webSocketService.addMessageHandler({
        identifier: 'gold_update_handler',
        messageType: "gold_update",
        callback: (message) => {
          if (matchState.isDM) {
            console.log("Gold Update:", message.msg, Object.keys(matchState.inventories), matchState.inventories[message.msg.playerid]);
            //matchState.game.players[message.msg.playerid].gold = message.msg.gold;
            matchState.inventories[message.msg.playerid].gold = message.msg.gold;
            matchState.game.players[message.msg.playerid].gold = message.msg.gold;
            updateMatchState([]); // stoopid
          } else {
            console.log("Gold Update:", message.msg);
            matchState.game.players[message.msg.playerid].gold = message.msg.gold;
            updateMatchState([]);
          }
        }
      });

      webSocketService.addMessageHandler({
        identifier: 'item_removal_handler',
        messageType: "item_removal",
        callback: (message) => {
          console.log("Item Removal:", message.msg);
          if (matchState.isDM) {
            delete matchState.inventories[message.msg.playerid].inventory[message.msg.itemid];
          } else {
            delete matchState.inventory[message.msg.itemid];
          }
          updateMatchState([]); // stoopid
        }
      });

      webSocketService.addMessageHandler({
        identifier: 'loot_list_handler',
        messageType: "loot_list_update",
        callback: (message) => {
          console.log("loot_list_update:", message.msg);
          matchState.loot = message.msg;
          updateMatchState([]); // stoopid
        }
      });

      webSocketService.retryHandlingCallback = retryHandlingCallback;

    });
  
    const playerSelected = (playerid) => {
      console.log("Selected player:", playerid)
      setSelectedPlayerID(playerid);
      if (playerid === -1) {
        console.log("Dungeon Master selected");
        handleOpenModal();
      } else {
        console.log ("Player selected", matchState.game.game.id, playerid);
        webSocketService.sendMessage({
          type: "selectPlayer", 
          playerid: playerid,
          gameid: matchState.game.game.id
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
        gameid: matchState.game.game.id,
        dm_pass: input
      });
    };

    const retryHandlingCallback = (count) => {

      if (count === -1) {
        console.log("Connection established.");
        setRetryConnecting(false);
        setRetryCount(0);
        return;
      }

      if (count >= 30) {
        console.log("Connection lost. Cleaning up.");
        updateMatchState({
          isDM : false,
          player: null,
          game: null,
        });
        alert("Connection lost. You will need to rejoin the game.")
        return;
      }

      setRetryConnecting(true);
      setRetryCount(count);
    };

    if (retryConnecting) {
      return (
        <div style={{ textAlign: 'center', fontSize: "24px", color:"grey" }}>
          <div className="spinner"></div>
          <p>Connection lost. Trying to reconnect. Try: {retryCount}</p>
        </div>
      );
    }

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
      return <PlayerView />;
    }
  }
  
  export default Game;
  