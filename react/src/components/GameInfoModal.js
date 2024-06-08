import React from 'react';
import './GameInfoModal.css';

const GameInfoModal = ({ isOpen, gameName, joinCode, onClose, importItems }) => {
  if (!isOpen) return null;

  return (
    <div className="game-info-modal-overlay" onClick={onClose}>
      <div className="game-info-modal" onClick={(e) => e.stopPropagation()}>
        <div className="game-info-modal-header">
          <h3 className="game-info-modal-title">Game Information</h3>
          <button className="game-info-modal-close" onClick={onClose}>
            &times;
          </button>
        </div>
        <div className="game-info-modal-content">
          <p className="game-info-modal-text">
            Game Name: <span className="game-info-bold">{gameName}</span>
          </p>
          <p className="game-info-modal-text">
            Join Code: <span className="game-info-bold joincode">{joinCode}</span>
          </p>
          <div className="game-info-modal-buttons">
            <div className="game-info-modal-button" onClick={() => {importItems("DnD")}}>Import DnD</div>
            <div className="game-info-modal-button notImplemented">Import Extra</div>
            <div className="game-info-modal-button notImplemented">Import DxD</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GameInfoModal;
