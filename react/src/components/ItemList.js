import React, { useState } from 'react';
import { useWebSocket } from './WebSocketContext';
import ItemModal from './ItemModal';
import './ItemList.css';

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

const Item = ({ name, description, value, image, onRightClick }) => {
  if (!image) {
    image = 'https://www.dndbeyond.com/attachments/2/741/potion.jpg';
  }

  return (
    <div className="item-container"
      onContextMenu={(e) => {
        e.preventDefault();
        onRightClick(e);
      }}
    >
      <img src={image} alt={name} className="item-image" />
      <div className="item-content">
        <div className="item-name">{name}</div>
        <div className="item-description">{description}</div>
        <div className="item-value">{`${value}GP`}</div>
      </div>
    </div>
  );
};

const ItemList = ({ items, players }) => {
  const [sortType, setSortType] = useState('name');
  const [contextMenu, setContextMenu] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
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

  const sortedItems = [...items]
    .filter(item => item.name.toLowerCase().includes(searchTerm.toLowerCase()))
    .sort((a, b) => {
      if (sortType === 'name') {
        return a.name.localeCompare(b.name);
      } else if (sortType === 'id') {
        return b.id - a.id;
      } else {
        return b.value - a.value;
      }
    });

  const handleRightClick = (e, item) => {
    setContextMenu({
      position: { x: e.pageX, y: e.pageY },
      options: [
        { label: 'Edit', onClick: () => console.log('Edit', item) },
        { label: 'Delete', onClick: () => console.log('Delete', item) },
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
            name={item.name}
            description={item.description}
            value={item.value}
            image={item.img}
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
      <ItemModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveNewItem}
      />
    </div>
  );
};

export default ItemList;
