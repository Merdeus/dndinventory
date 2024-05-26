import React, { useState } from 'react';
import { useWebSocket } from './WebSocketContext';
import ItemModal from './ItemModal';
import './ItemList.css';
import Item from './Item';

const rarityNames = {
  1: 'common',
  2: 'uncommon',
  3: 'rare',
  4: 'veryrare',
  5: 'epic',
  6: 'legendary',
  7: 'questitem',
};

const typeNames = {
  1: 'Weapon',
  2: 'Armor',
  3: 'Adventure Gear',
  4: 'Tool',
  5: 'Consumable',
  6: 'Magical Item',
  7: 'Valuable',
  8: '',
}

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

const ItemList = ({ items, players }) => {
  const [sortType, setSortType] = useState('name');
  const [filters, setFilters] = useState({
    name: '',
    rarity: '',
    value: '',
  });
  const [contextMenu, setContextMenu] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const webSocketService = useWebSocket();

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleAddNewItem = () => {
    setIsModalOpen(true);
  };

  const handleSaveNewItem = (newItem) => {
    console.log('New item saved:', newItem);
    setIsModalOpen(false);

    webSocketService.sendMessage({
      type: 'AddItem',
      item: newItem,
    });

  };

  const handleEditItem = (item) => {
    setEditItem(item);
  };

  const handleSaveEditItem = (item) => {
    console.log('Edit item saved:', item);
    item.id = editItem.id;
    webSocketService.sendMessage({
      type: 'EditItem',
      item: item,
    });
    setEditItem(null);
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
      } else if (sortType === 'type') {
        return b.type - a.type;
      } else {
        return b.value - a.value;
      }
    });

  const handleRightClick = (e, item) => {
    setContextMenu({
      position: { x: e.pageX, y: e.pageY },
      options: [
        { label: 'Edit', onClick: () => handleEditItem(item) },
        { label: 'Delete', onClick: () => {
          webSocketService.sendMessage({
            type: 'DeleteItemPrefab',
            item_id: item.id
          });
        }},
        (players.length > 0 && players[0].id !== 0) ? {
          label: 'Give to',
          submenu: players.map(player => ({
            label: player.name,
            onClick: () => {
              console.log('DM: Give to', player.name, item);
              webSocketService.sendMessage({
                type: 'GiveItem',
                player_id: player.id,
                item_id: item.id,
              });
            }
          }))
        } : { label: 'No players', onClick: () => {} },
      ],
    });
  };

  const handleCloseContextMenu = () => {
    setContextMenu(null);
  };

  return (
    <div className="inventory-container">
      <div className="inventory-header">
        <h2>Items</h2>

        <div className='sort-div'>
          <div className="sort-label">Sort by:</div>
          <div className="sort-buttons">
            <button className={sortType === 'name' ? 'selected' : ''} onClick={() => setSortType('name')}>Name</button>
            <button className={sortType === 'rarity' ? 'selected' : ''} onClick={() => setSortType('rarity')}>Rarity</button>
            <button className={sortType === 'type' ? 'selected' : ''} onClick={() => setSortType('type')}>Type</button>
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
        <button className="add-item-button" onClick={handleAddNewItem}>
          &#43; {/* Plus symbol */}
        </button>
      </div>
      <div className="inventory-list">
        {sortedItems.map(item => (
          <Item
            key={item.id}
            id={item.id}
            name={item.name}
            description={item.description}
            value={item.value}
            image={item.img}
            type={item.type}
            rarity={rarityNames[item.rarity]}
            isDraggable={true}
            onRightClick={(e) => handleRightClick(e, item)}
          />
        ))}
      </div>
      {contextMenu && (
        <ContextMenu
          position={contextMenu.position}
          options={contextMenu.options}
          onClose={handleCloseContextMenu}
        />
      )}

      {editItem && (
      <ItemModal
        prevStuff={editItem}
        isOpen={true}
        onClose={() => setEditItem(null)}
        onSave={handleSaveEditItem}
      />
      )}

      <ItemModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveNewItem}
      />
    </div>
  );
};

export default ItemList;
