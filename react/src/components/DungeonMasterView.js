// DungeonMaster.js
import React, { useState, useEffect } from 'react';
import Inventory from './Inventory';
import { useMatch } from './MatchContext';
import { useSSE } from './SSEContext';
import ItemList from './ItemList';
import './DungeonMasterView.css';
import PlayerList from './PlayerList';
import LootList from './LootList';
import GameInfoModal from './GameInfoModal';

import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const DungeonMasterView = () => {

  const [players, setPlayers] = useState([]);
	const [selectedPlayer, setSelectedPlayer] = useState("None");
  const [allowedToSell, setAllowedToSell] = useState(false);
  const [currentLeftTab, setCurrentLeftTab] = useState("Items");
  const [currentRightTab, setCurrentRightTab] = useState("Inventories");

	const { matchState, updateMatchState } = useMatch();
	const [itemlist, setitemlist] = useState([]);
  const [isGameInfoModalOpen, setIsGameInfoModalOpen] = useState(false); // Step 2: Define state
  const webSocketService = useSSE();


  const handleOpenGameInfoModal = () => {
    setIsGameInfoModalOpen(true);
  };

  const handleCloseGameInfoModal = () => {
    setIsGameInfoModalOpen(false);
  };

  const importItems = (items) => {
    console.log("DM: Importing items:", items);
    setIsGameInfoModalOpen(false);

    if (webSocketService.messageHandlers.find(h => h.identifier === "import_items_handler")) {
      toast.error('Already importing items!')
      return;
    }
    const toastId = toast.loading('Importing items...', {
      position: "top-right",
      autoClose: false,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
      progress: undefined,
      theme: "dark",
      });

    webSocketService.sendMessage({
      type: 'ImportNewItems',
      items: items
    });

    const handler = {
      identifier: 'import_items_handler',
      messageType: "items_imported",
      callback: (message) => {
        if (message.success) {
          toast.update(toastId, {
            render: 'Items imported successfully!',
            type: 'success',
            isLoading: false,
            autoClose: 3000
          });
        } else {
          toast.update(toastId, {
            render: 'Error importing items!',
            type: 'error',
            isLoading: false,
            autoClose: 3000
          });
        }
        webSocketService.removeMessageHandler(handler);
      }
    };

    webSocketService.addMessageHandler(handler);
  }

  useEffect(() => {
  
    if (Object.values(matchState.inventories).length <= 0) {
        setPlayers([
            { id: 0, name: 'None', inventory: [] }
        ])
    } else {
        setPlayers(Object.values(matchState.inventories))
        setSelectedPlayer(Object.values(matchState.inventories)[0].name)
    }
  }, [matchState.inventories]);

  useEffect(() => {
    setitemlist(matchState.itemlist)
  }, [matchState.itemlist]);


  useEffect(() => {

    webSocketService.addMessageHandler({
      identifier: 'dm_error_display',
      messageType: "error",
      callback: (message) => {
        toast.error(message.msg, {
          autoClose: 3000
        });
      }
    });
  }, []);



  const handleSelectPlayer = (event) => {
    setSelectedPlayer(event.target.value);
  };

  const getSelectedPlayerInventory = () => {
    const player = players.find(p => p.name === selectedPlayer);
    return player ? Object.values(player.inventory) : [];
  };

  const getSelectedPlayer = () => {
    const player = players.find(p => p.name === selectedPlayer);
    return player;
  };

  const handleAllowSelling = () => {
    setAllowedToSell(!allowedToSell);
  }

  const switchLeftTab = (tab) => {
    setCurrentLeftTab(tab);
  }

  const switchRightTab = (tab) => {
    setCurrentRightTab(tab);
  }

  // setPlayerGold function
  const setPlayerGold = (player, gold) => {
    console.log("DM: New Gold value set for player:", gold, player);
    webSocketService.sendMessage({
      type: 'SetPlayerGold',
      player_id: player.id,
      gold: gold,
    });
  };

  const deleteItem = (item) => {
    console.log('DM: Delete item:', item);
    toast.info(`Deleted a Item from ${selectedPlayer}`, {
      autoClose: 3000
    })
    webSocketService.sendMessage({
      type: 'DeleteItem',
      item_id: item
    });
  }

  const giveItem = (player, item) => {
    console.log('DM: Give item:', item, 'to player:', player);
    webSocketService.sendMessage({
      type: 'GiveItem',
      player_id: player,
      item_id: item,
    })};

  if (players.length < 1) {
    return <div>Loading...</div>;
  } else {
    return (
      <div style={styles.container}>
        <div style={styles.leftPanel}>
          <div className="button-panel">
            <button className={allowedToSell ? "panel-button buttonAllowed" : "panel-button buttonDisallowed"} onClick={handleAllowSelling} >{allowedToSell ? "Selling allowed" : "Selling disallowed"}</button>
            <button className={currentLeftTab === "Items" ? "panel-button buttonSelected" : "panel-button"} onClick={() => {switchLeftTab("Items")}}>Items</button>
            <button className={currentLeftTab === "Players" ? "panel-button buttonSelected" : "panel-button"} onClick={() => {switchLeftTab("Players")}}>Players</button>
            <button className="panel-button buttonWaySmaller" onClick={handleOpenGameInfoModal}>Info</button>
          </div>
          {currentLeftTab === "Items" && <ItemList items={itemlist} players={players} />}
          {currentLeftTab === "Players" && <PlayerList players={players} setPlayerGold={setPlayerGold} />}
          
        </div>
        <div style={styles.rightPanel}>
          
          <div className="button-panel">
            <button className={currentRightTab === "Inventories" ? "panel-button buttonSelected" : "panel-button"} onClick={() => { switchRightTab("Inventories") }}>Inventories</button>
            <button className={currentRightTab === "Shops" ? "panel-button buttonSelected" : "panel-button"} onClick={() => { switchRightTab("Shops") }}>Shops</button>
            <button className={currentRightTab === "Loot" ? "panel-button buttonSelected" : "panel-button"} onClick={() => {switchRightTab("Loot")}}>Loot</button>
          </div>
          {currentRightTab === "Inventories" && (
            <>
              <div style={styles.playerSelect}>
                <select value={selectedPlayer} onChange={handleSelectPlayer} style={styles.select}>
                  {(players).map(player => (
                    <option key={player.name} value={player.name}>
                      {player.name}
                    </option>
                  ))}
                </select>
              </div>
              <Inventory
                id={getSelectedPlayer().id}
                items={getSelectedPlayerInventory()}
                players={players}
                isDMView={true}
                giveItem={giveItem}
                deleteItem={deleteItem}
              />
            </>
          )}
          {currentRightTab === "Loot" && <LootList items={Object.values(matchState.loot.items)} currentGold={matchState.loot.gold} isDM={true} />}

        </div>
        <GameInfoModal
            isOpen={isGameInfoModalOpen}
            gameName={matchState.game.game.name}
            joinCode={matchState.game.game.join_code}
            importItems={importItems}
            onClose={handleCloseGameInfoModal}
          />
          <ToastContainer
            position="top-right"
            autoClose={false}
            newestOnTop={false}
            closeOnClick={true}
            rtl={false}
            pauseOnFocusLoss
            draggable
            theme="dark"
          />
      </div>
    );
  }
};

const styles = {
  container: {
    display: 'flex',
    height: '100vh',
  
  },
  leftPanel: {
    flex: 1,
    borderRight: '2px solid #000000',
    borderRadius: '20px 0 0 20px', // Curved border on the right side
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    paddingTop: '30px',
    paddingBottom: '30px',
    width: "47vw"
  },
  rightPanel: {
    flex: 1,
    borderLeft: '2px solid #000000',
    borderRadius: '0 20px 20px 0', // Curved border on the left side
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    paddingTop: '30px',
    paddingBottom: '30px',
    width: "47vw"
  },
  playerSelect: {
    width: '100%',
    marginBottom: '10px',
    textAlign: 'center',
  },
  select: {
    width: '80vh',
    padding: '10px',
    borderRadius: '5px',
    border: '1px solid #ccc',
    fontSize: '16px',
    backgroundColor: '#555',
    border: "2px solid #ccbd32",
    color: '#fdfdfd',
  },
  ptop: {
      fontSize: "18px",
      color: '#fdfdfd',
      marginBottom: "12px",
      marginTop: "2px"
  }
};

export default DungeonMasterView;
