import React, { useState } from 'react';
import './Inventory.css';


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
  



const Item = ({ name, description, value, image, onRightClick }) => {

    // if item is not provided, use a default image
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


const Inventory = ({ items, players, isDMView, deleteItem }) => {
  const [sortType, setSortType] = useState('id');
  const [contextMenu, setContextMenu] = useState(null);

  if (!deleteItem)
    deleteItem = (item) => console.log('DeleteItem not implemented: ', item);

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
      options.push({ label: 'Sell', onClick: () => console.log('Sell', item) });
    }
  
    options.push(
      { label: 'Delete', onClick: () => deleteItem(item) },
      {
        label: 'Send to',
        submenu: players.map(player => ({
          label: player.name,
          onClick: () => console.log(`Send ${item.name} to ${player.name}`)
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

  return (
    <div className="inventory-container">
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

    </div>
  );
};

export default Inventory;
