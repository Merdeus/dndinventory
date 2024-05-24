// DungeonMaster.js
import React, { useState, useEffect } from 'react';
import Inventory from './Inventory';
import { useMatch } from './MatchContext';
import { useWebSocket } from './WebSocketContext';
import ItemList from './ItemList';
import './DungeonMasterView.css';
import PlayerList from './PlayerList';

const DungeonMasterView = () => {

  const [players, setPlayers] = useState([]);
	const [selectedPlayer, setSelectedPlayer] = useState("None");
  const [allowedToSell, setAllowedToSell] = useState(false);
  const [currentLeftTab, setCurrentLeftTab] = useState("Items");
	const { matchState, updateMatchState } = useMatch();
	const [itemlist, setitemlist] = useState([]);

  useEffect(() => {
  
    if (matchState.inventories.length <= 0) {
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
    console.log("Players updated:", players)
  }, [players]);



  const handleSelectPlayer = (event) => {
    setSelectedPlayer(event.target.value);
  };

  const getSelectedPlayerInventory = () => {
    const player = players.find(p => p.name === selectedPlayer);
    return player ? Object.values(player.inventory) : [];
  };

  const handleAllowSelling = () => {
    setAllowedToSell(!allowedToSell);
  }

  const switchLeftTab = (tab) => {
    setCurrentLeftTab(tab);
  }

  const webSocketService = useWebSocket();
  // setPlayerGold function
  const setPlayerGold = (player, gold) => {
    console.log("DM: New Gold value set for player:", gold, player);
    webSocketService.sendMessage({
      type: 'SetPlayerGold',
      player_id: player.id,
      gold: gold,
    });
  };

  if (players.length < 1) {
    return <div>Loading...</div>;
  } else {
    return (
      <div style={styles.container}>
        <div style={styles.leftPanel}>
          <div className="button-panel">
            <button className={allowedToSell ? "panel-button buttonBigger buttonAllowed" : "panel-button buttonBigger buttonDisallowed"} onClick={handleAllowSelling} >{allowedToSell ? "Selling allowed" : "Selling disallowed"}</button>
            <button className={currentLeftTab === "Items" ? "panel-button buttonSmaller buttonSelected" : "panel-button buttonSmaller"} onClick={() => {switchLeftTab("Items")}}>Items</button>
            <button className={currentLeftTab === "Shops" ? "panel-button buttonSmaller buttonSelected" : "panel-button buttonSmaller"} onClick={() => {switchLeftTab("Shops")}}>Shops</button>
            <button className={currentLeftTab === "Loot" ? "panel-button buttonSmaller buttonSelected" : "panel-button buttonSmaller"} onClick={() => {switchLeftTab("Loot")}}>Loot</button>
            <button className={currentLeftTab === "Players" ? "panel-button buttonSmaller buttonSelected" : "panel-button buttonSmaller"} onClick={() => {switchLeftTab("Players")}}>Players</button>
          </div>
          {currentLeftTab === "Items" && <ItemList items={itemlist} players={players} />}
          {currentLeftTab === "Players" && <PlayerList players={players} setPlayerGold={setPlayerGold} />}
        </div>
        <div style={styles.rightPanel}>
          
          <div style={styles.playerSelect}>
          <p style={styles.ptop}>Select a players inventory</p>
            <select value={selectedPlayer} onChange={handleSelectPlayer} style={styles.select}>
              {(players).map(player => (
                <option key={player.name} value={player.name}>
                  {player.name}
                </option>
              ))}
            </select>
          </div>
          <Inventory items={getSelectedPlayerInventory()} players={players} isDMView={true} />
        </div>
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
    borderRight: '1px solid #ccc',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '30px'
  },
  rightPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '30px'
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
