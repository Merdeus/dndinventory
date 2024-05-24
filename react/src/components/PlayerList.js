import React, {useState} from 'react';
import './PlayerList.css';
import { useWebSocket } from './WebSocketContext';

const GoldModal = ({ prevGold, onClose, onSubmit }) => {
	const [goldChange, setGoldChange] = useState(prevGold || 0);
  
	const handleGoldChange = (amount) => {
	  setGoldChange(Math.max(goldChange + amount, 0));
	};
  
	const handleInputChange = (event) => {
	  setGoldChange(parseInt(event.target.value) || 0);
	};
  
	const handleCancel = () => {
	  setGoldChange(0);
	  onClose();
	};
  
	const handleSubmit = () => {
	  onSubmit(goldChange);
	  setGoldChange(0);
	  onClose();
	};
  
	return (
		<div className="modal-overlay"><div className="modal">
	  <div className="gold-modal">
		<div className="button-row">
		  <div className="gold-button" onClick={() => handleGoldChange(1)}>+1</div>
		  <div className="gold-button" onClick={() => handleGoldChange(10)}>+10</div>
		  <div className="gold-button" onClick={() => handleGoldChange(100)}>+100</div>
		  <div className="gold-button" onClick={() => handleGoldChange(1000)}>+1000</div>
		</div>
		<div className="button-row">
		  <div className="gold-button" onClick={() => handleGoldChange(-1)}>-1</div>
		  <div className="gold-button" onClick={() => handleGoldChange(-10)}>-10</div>
		  <div className="gold-button" onClick={() => handleGoldChange(-100)}>-100</div>
		  <div className="gold-button" onClick={() => handleGoldChange(-1000)}>-1000</div>
		</div>
		<input type="number" value={goldChange} onChange={handleInputChange} className="gold-input" />
		<div className="button-row-last">
		  <div className="gold-button cancel-button" onClick={handleCancel}>Cancel</div>
		  <div className="gold-button submit-button" onClick={handleSubmit}>Submit</div>
		</div>
	  </div></div></div>
	);
};

const CreatePlayerModal = ({ isOpen, onClose, onSubmit }) => {
    const [name, setName] = useState('');
    const [gold, setGold] = useState(0);
  
    const handleNameChange = (e) => setName(e.target.value);
    const handleGoldChange = (e) => setGold(e.target.value);
  
    const handleSubmit = () => {
      onSubmit({ name, gold: parseInt(gold, 10) });
      setName('');
      setGold('');
    };
  
    if (!isOpen) {
      return null;
    }
  
    return (
      <div className="modal-overlay">
        <div className="modal">
          <h2>Create New Player</h2>
          <div className="modal-content">
            <label>
              Player Name:
              <input type="text" value={name} onChange={handleNameChange} />
            </label>
            <label>
              Starting Gold:
              <input type="number" value={gold} onChange={handleGoldChange} />
            </label>
          </div>
          <div className="modal-actions">
            <button onClick={handleSubmit}>Create</button>
            <button onClick={onClose}>Cancel</button>
          </div>
        </div>
      </div>
    );
  };

const PlayerList = ({ players, setPlayerGold, onButtonClick2 }) => {

    const [isCreatePlayerModalOpen, setIsCreatePlayerModalOpen] = useState(false);
	const webSocketService = useWebSocket();


	const [showGoldModal, setShowGoldModal] = useState(false);
	const [currentGold, setCurrentGold] = useState(false);
	const [currentPlayer, setCurrentPlayer] = useState(null);

	const handleOpenGoldModal = (player) => {
		setCurrentPlayer(player);
		setCurrentGold(player.gold);
	  	setShowGoldModal(true);
	};
  
	const handleCloseGoldModal = () => {
	  setShowGoldModal(false);
	};
  
	const handleGoldSubmit = (goldValue) => {
		setPlayerGold(currentPlayer, goldValue);
		setShowGoldModal(false);
	};


	const handleOpenCreatePlayerModal = () => {
		setIsCreatePlayerModalOpen(true);
	};

	const handleCloseCreatePlayerModal = () => {
		setIsCreatePlayerModalOpen(false);
	};

	  const handleSubmitNewPlayer = (player) => {
		console.log("New player:", player);
		if (player.name=== "") {
			alert("Please enter a valid name for the player.");
			return;
		}

		if (isNaN(player.gold))
			player.gold = 0;

		player.gold = Math.max(0, player.gold);

		// Send the new player to the server
		webSocketService.sendMessage({
			type: "CreatePlayer", 
			player_name: player.name,
			gold: player.gold
		});

		handleCloseCreatePlayerModal();
	  };


  return (
	<>
		<div className="player-list-container">
			<div className="player-container centerPlayerContainer" onClick={handleOpenCreatePlayerModal}>
				Create new player
			</div>
		{players.map(player => (
			<div key={player.id} className="player-container">
			<div className="player-content">
				<div className="player-name">{player.name || "None"}</div>
				<div className="player-gold">{`${player.gold || 0} GP`}</div>
			</div>
			{players[0].id !== 0 && (
				<div className="player-buttons">
					<button className="small-button" onClick={() => alert("Open it yourself")}>View Inventory</button>
					<button className="small-button buttonGold" onClick={() => handleOpenGoldModal(player)}>Gold</button>
					<button className="small-button buttonDelete" onClick={() => onButtonClick2(player)}>Delete</button>
				</div>
			)}

			</div>
		))}
		</div>
		<CreatePlayerModal
			isOpen={isCreatePlayerModalOpen}
			onClose={handleCloseCreatePlayerModal}
			onSubmit={handleSubmitNewPlayer}
		/>
		{showGoldModal && (
			<GoldModal prevGold={currentGold} onSubmit={handleGoldSubmit} onClose={handleCloseGoldModal} />
		)}
	</>
  );
};

export default PlayerList;
