import React, { useState } from 'react';
import { useMatch } from './MatchContext';
import './Inventory.css';
import Item from './Item';

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

const typeNames = {
  1: 'Weapon',
  2: 'Armor',
  3: 'Adventure Gear',
  4: 'Tool',
  5: 'Consumable',
  6: 'Magical Item',
  7: 'Valuable',
  8: 'Scroll',
  9: 'Shield',
  10: 'Ring',
  11: 'Staff',
  12: 'Miscellaneous',
  13: 'Wondrous Item',
}

const ContextMenu = ({ position, options, onClose }) => {
    const [submenuPosition, setSubmenuPosition] = useState(null);
    const [submenuOptions, setSubmenuOptions] = useState([]);
  
    const handleMouseEnter = (option, index) => {
      if (option.submenu) {
        setSubmenuPosition({ x: position.x + 150, y: position.y - index*20 });
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

const Inventory = ({ id, items, players, isDMView, deleteItem, giveItem, sellItem }) => {
  const [sortType, setSortType] = useState('id');
  const [contextMenu, setContextMenu] = useState(null);
  const { matchState } = useMatch();

  if (!deleteItem)
    deleteItem = (item) => console.log('DeleteItem not implemented: ', item);

  if (!giveItem)
    giveItem = (player, item) => console.log('GiveItem not implemented: ', player, item);

  const sortedItems = [...items].sort((a, b) => {
    if (sortType === 'name') {
        return a.name.localeCompare(b.name);
    } else if (sortType === 'id') {
        return b.id - a.id;
    } else {
        return b.value - a.value;
    }
  });

  const handleRightClick = (e, item) => {
    const options = [];

    if (!isDMView) {
      options.push({ label: 'Sell', onClick: () => sellItem(item.id) });
    }
  
    options.push(
      { label: 'Delete', onClick: () => deleteItem(item.id) },
      {
        label: 'Send to',
        submenu: players
        .filter(player => player.id !== matchState.player)
        .map(player => ({
          label: player.name,
          onClick: () => {
            console.log(`Send ${item.name} to ${player.name}`);
            giveItem(player.id, item.id);
        }
        }))
      }
    );
  
    setContextMenu({
      position: { x: e.pageX, y: e.pageY },
      options,
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
    console.log(e, e.dataTransfer.getData('id'));
    const itemId = e.dataTransfer.getData('id');
    giveItem(id, itemId);
  };


  return (
    <div className="inventory-container" onDragOver={handleDragOver} onDrop={handleDrop}>
      <div className="inventory-header">
        <h2>Inventory</h2>
        <div className='sort-div'>
            <div className="sort-label">Sort by:</div>
            <div className="sort-buttons">
                <button className={sortType === 'id' ? 'selected' : ''} onClick={() => setSortType('id')}>Latest</button>
                <button className={sortType === 'name' ? 'selected' : ''} onClick={() => setSortType('name')}>Name</button>
                <button className={sortType === 'value' ? 'selected' : ''} onClick={() => setSortType('value')}>Value</button>
            </div>
        </div>
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
            count={item.count}
            rarity={rarityNames[item.rarity]}
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

    </div>
  );
};

export default Inventory;
