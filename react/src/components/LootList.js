import React, { useState } from 'react';
import { useWebSocket } from './WebSocketContext';
import { useMatch } from './MatchContext';
import ItemModal from './ItemModal';
import './LootList.css';
import LootModal from './LootModal';
import GoldModal from './GoldModal';
import Item from './Item';
import PlayerSelectModal from './PlayerSelectModal';


const rarityNames = {
  0: 'mundane',
  1: 'common',
  2: 'uncommon',
  3: 'rare',
  4: 'veryrare',
  5: 'epic',
  6: 'legendary',
  7: 'questitem',
};

const ContextMenu = ({ position, options, onClose }) => {
  const [submenuPosition, setSubmenuPosition] = useState(null);
  const [submenuOptions, setSubmenuOptions] = useState([]);

  const handleMouseEnter = (option, index) => {
    if (option.submenu) {
      setSubmenuPosition({ x: position.x + 150, y: position.y - index * 20 });
      setSubmenuOptions(option.submenu);
    } else {
      setSubmenuPosition(null);
      setSubmenuOptions([]);
    }
  };

  return (
    <div
      className="context-menu"
      style={{ top: position.y, left: position.x }}
      onMouseLeave={onClose}
    >
      {options.map((option, index) => (
        <div
          key={index}
          className="context-menu-item"
          onClick={() => {
            if (!option.submenu) {
              option.onClick();
              onClose();
            }
          }}
          onMouseEnter={() => handleMouseEnter(option, index)}
        >
          {option.label}
        </div>
      ))}
      {submenuOptions.length > 0 && (
        <div
          className="context-menu submenu"
          style={{ top: position.y - submenuPosition.y, left: 90 }}
        >
          {submenuOptions.map((option, index) => (
            <div
              key={index}
              className="context-menu-item"
              onClick={() => {
                option.onClick();
                onClose();
              }}
            >
              {option.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const LootList = ({ items, currentGold }) => {
  const [sortType, setSortType] = useState('name');
  const [contextMenu, setContextMenu] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLootModalOpen, setIsLootModalOpen] = useState(false);
  const [isPlayerSelectModalOpen, setIsPlayerSelectModalOpen] = useState(false);
  const [goldAmount, setGoldAmount] = useState(currentGold);
  const [showGoldModal, setShowGoldModal] = useState(false);
  const webSocketService = useWebSocket();
  const { matchState, updateMatchState } = useMatch();

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleLootModalSubmit = (count) => {  
    webSocketService.sendMessage({
      type: 'GenerateLootItems',
      count_list: count,
    });
    setIsLootModalOpen(false);
  }

  const handleLootModalClose = () => {
    setIsLootModalOpen(false);
  }

  const sortedItems = [...items]
    .filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase()))
    .sort((a, b) => {
      if (sortType === 'name') {
        return a.name.localeCompare(b.name);
      } else if (sortType === 'id') {
        return b.id - a.id;
      } else if (sortType === 'rarity') {
        return b.rarity - a.rarity;
      } else {
        return b.value - a.value;
      }
    });

  const handleRightClick = (e, item) => {
    setContextMenu({
      position: { x: e.pageX, y: e.pageY },
      options: [
        { label: 'Delete', onClick: () => {
          webSocketService.sendMessage({
            type: 'RemoveLootItem',
            loot_id: item.lootid
          });
        }},
      ],
    });
  };

  const handleCloseContextMenu = () => {
    setContextMenu(null);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const itemId = e.dataTransfer.getData('id');
    webSocketService.sendMessage({
      type: 'AddLootItem',
      item_id: itemId,
    });
  };

  const handleOpenGoldModal = (player) => {
	  	setShowGoldModal(true);
	};
  
	const handleCloseGoldModal = () => {
	  setShowGoldModal(false);
	};
  
	const handleGoldSubmit = (goldValue) => {
    webSocketService.sendMessage({
      type: 'SetLootGold',
      loot_gold: goldValue,
    });
    setGoldAmount(goldValue);
		setShowGoldModal(false);
	};

  const clearLootTable = () => {
    webSocketService.sendMessage({
      type: 'ClearLoot',
    });
  }

  const handleOpenPlayerSelectModal = () => {
    setIsPlayerSelectModalOpen(true);
  }

  const handleClosePlayerSelectModal = () => {
    setIsPlayerSelectModalOpen(false);
  }

  const handlePlayerSelectModalSubmit = (players) => {
    webSocketService.sendMessage({
      type: 'DistributeLoot',
      players: players,
    });
    setIsPlayerSelectModalOpen(false);
  }


  return (
    <>
    <div className="inventory-container" onDragOver={handleDragOver} onDrop={handleDrop}>
      <div className="inventory-header">
        <h2>Loot</h2>
        <h3>Current Gold: {goldAmount}</h3>
        <div className='sort-div'>
          <div className="sort-label">Sort by:</div>
          <div className="sort-buttons">
            <button className={sortType === 'name' ? 'selected' : ''} onClick={() => setSortType('name')}>Name</button>
            <button className={sortType === 'rarity' ? 'selected' : ''} onClick={() => setSortType('rarity')}>Rarity</button>
            <button className={sortType === 'value' ? 'selected' : ''} onClick={() => setSortType('value')}>Value</button>
          </div>
        </div>
      </div>
      <div className="inventory-search-add">
        <input
          type="text"
          placeholder="Search items..."
          value={searchTerm}
          onChange={handleSearchChange}
          className="search-input"
        />
        <button className="set-gold-button" onClick={handleOpenGoldModal}>
          G
        </button>
        <button className="loot-clear-button" onClick={clearLootTable}>
          X
        </button>
      </div>

      <div className="loot-container centerLootContainer" onClick={() => {setIsLootModalOpen(true)}}>
			  Generate Loot
	    </div>

      <div className="inventory-list">
        {sortedItems.map(item => (
          <Item
          key={item.lootid}
          id={item.id}
          name={item.name}
          description={item.description}
          value={item.value}
          image={item.img}
          type={item.type}
          count={item.count}
          rarity={rarityNames[item.rarity]}
          onRightClick={(e) => handleRightClick(e, item)}
        />
        ))}
      </div>
      <div className="loot-container centerLootContainer last" onClick={handleOpenPlayerSelectModal}>
			  Distribute loot
	    </div>
      {contextMenu && (
        <ContextMenu
          position={contextMenu.position}
          options={contextMenu.options}
          onClose={handleCloseContextMenu}
        />
      )}
    </div>
      {isLootModalOpen && (
        <LootModal
          onClose={handleLootModalClose}
          onSubmit={handleLootModalSubmit}
        />
      )}

      {showGoldModal && (
        <GoldModal prevGold={goldAmount} onSubmit={handleGoldSubmit} onClose={handleCloseGoldModal} />
      )}

      {isPlayerSelectModalOpen && (
        <PlayerSelectModal players={matchState.inventories} onClose={handleClosePlayerSelectModal} onSubmit={handlePlayerSelectModalSubmit} />
      )}
    
    </>
  );
};

export default LootList;
