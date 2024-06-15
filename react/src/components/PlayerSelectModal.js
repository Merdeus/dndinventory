import React, { useState } from 'react';
import './PlayerSelectModal.css';
import { useMatch } from './MatchContext';

const PlayerSelectModal = ({ players, onClose, onSubmit }) => {

  players = Object.values(players);
  const [selectedPlayers, setSelectedPlayers] = useState([]);

  const togglePlayerSelection = (playerId) => {
    setSelectedPlayers((prevSelectedPlayers) => ({
      ...prevSelectedPlayers,
      [playerId]: !prevSelectedPlayers[playerId],
    }));
  };

  const handleCancel = () => {
    setSelectedPlayers(
      players.reduce((acc, player) => {
        acc[player.id] = false;
        return acc;
      }, {})
    );
    onClose();
  };

  const handleSubmit = () => {

    if (Object.keys(selectedPlayers).filter((playerId) => selectedPlayers[playerId]).length === 0) {
      alert('You must select at least one player');
      return;
    }

    const activatedPlayers = Object.keys(selectedPlayers).filter(
      (playerId) => selectedPlayers[playerId]
    );
    console.log(activatedPlayers);
    onSubmit(activatedPlayers);
    onClose();
  };

  return (
    <div className="playerselectmodal-overlay">
      <div className="playerselectmodal">
        <div className="playerselectmodal-title">Select Players</div>
        <div className="playerselectmodal-subtitle">Select all players which should receive this lootpool</div>
        <div className="playerselectmodal-list">
          {players.map((player) => (
            <div
              key={player.id}
              className={`playerselectmodal-player ${selectedPlayers[player.id] ? 'selected' : ''}`}
              onClick={() => togglePlayerSelection(player.id)}
            >
              {player.name}
            </div>
          ))}
        </div>
        <div className="playerselectmodal-button-row">
          <div className="playerselectmodal-button cancel-button" onClick={handleCancel}>
            Cancel
          </div>
          <div className="playerselectmodal-button submit-button" onClick={handleSubmit}>
            Submit
          </div>
        </div>
      </div>
    </div>
  );
};


const PlayerVoteModal = ({ players, onClose, onSubmit }) => {

  players = Object.values(players);
  const [selectedPlayer, setSelectedPlayer] = useState(-1);
  const { matchState, updateMatchState } = useMatch();

  const togglePlayerSelection = (playerId) => {
    setSelectedPlayer(playerId);
  };

  const handleCancel = () => {
    onClose();
  };

  const handleSubmit = () => {

    if (selectedPlayer === -1) {
      alert('You must select a player');
      return;
    }

    onSubmit(selectedPlayer);
    onClose();
  };

  return (
    <div className="playerselectmodal-overlay">
      <div className="playerselectmodal">
        <div className="playerselectmodal-title">Vote for Player</div>
        <div className="playerselectmodal-subtitle">Select the player who should receive this item</div>
        <div className="playerselectmodal-list">
          {players.map((player) => matchState.loot.players.includes(player.id) ? (
            <div
              key={player.id}
              className={`playerselectmodal-player ${selectedPlayer === player.id ? 'selected' : ''}`}
              onClick={() => togglePlayerSelection(player.id)}
            >
              {player.name}
            </div>
          ) : null)}
        </div>
        <div className="playerselectmodal-button-row">
          <div className="playerselectmodal-button cancel-button" onClick={handleCancel}>
            Cancel
          </div>
          <div className="playerselectmodal-button submit-button" onClick={handleSubmit}>
            Submit
          </div>
        </div>
      </div>
    </div>
  );
};

export {PlayerSelectModal, PlayerVoteModal};
