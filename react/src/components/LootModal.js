import React, { useState } from 'react';
import './LootModal.css';

const presetLootList = {
    "0" : {
        common: 0,
        uncommon: 0,
        rare: 0,
        veryRare: 0,
        epic: 0,
        legendary: 0
    },
    "1" : {
        common: 3,
        uncommon: 0,
        rare: 0,
        veryRare: 0,
        epic: 0,
        legendary: 0
    },
    "2" : {
        common: 2,
        uncommon: 2,
        rare: 0,
        veryRare: 0,
        epic: 0,
        legendary: 0
    },
    "3" : {
        common: 2,
        uncommon: 2,
        rare: 2,
        veryRare: 0,
        epic: 0,
        legendary: 0
    },
    "4" : {
        common: 0,
        uncommon: 2,
        rare: 2,
        veryRare: 3,
        epic: 0,
        legendary: 0
    },
    "5" : {
        common: 0,
        uncommon: 0,
        rare: 1,
        veryRare: 2,
        epic: 2,
        legendary: 0
    },
    "6" : {
        common: 0,
        uncommon: 0,
        rare: 0,
        veryRare: 1,
        epic: 2,
        legendary: 2
    }
}

const LootModal = ({ onClose, onSubmit }) => {
  const [lootType, setLootType] = useState("Common");

  const [counts, setCounts] = useState({
    common: 0,
    uncommon: 0,
    rare: 0,
    veryRare: 0,
    epic: 0,
    legendary: 0
  });
  const [uniqueAllowed, setUniqueAllowed] = useState(false);


  const handleLootTypeChange = (event) => {
    setCounts(presetLootList[event.target.value]);
  };

  const handleSubmit = () => {
    onSubmit(counts);
  };

  return (
    <div className="modal-overlay">
        <div className="modal">
            <div className="loot-modal">
                <h2>Generate Loot</h2>
                <div className="preset-dropdown">
                    <select onChange={handleLootTypeChange}>
                    <option value="0">Custom</option>
                    <option value="1">Preset: Common</option>
                    <option value="2">Preset: Uncommon</option>
                    <option value="3">Preset: Rare</option>
                    <option value="4">Preset: Very Rare</option>
                    <option value="5">Preset: Epic</option>
                    <option value="6">Preset: Legendary</option>
                    </select>
                </div>

                <div className="lootmodal-item-count">

                    <div>
                    # of Common Items:
                    <input
                        type="number"
                        value={counts.common}
                        onChange={(e) => setCounts({ ...counts, common: Math.max(parseInt(e.target.value),0)})}
                    />
                    </div>

                    <div>
                    # of Uncommon Items:
                    <input
                        type="number"
                        value={counts.uncommon}
                        onChange={(e) => setCounts({ ...counts, uncommon: Math.max(parseInt(e.target.value),0)})}
                    />
                    </div>

                    <div>
                    # of Rare Items:
                    <input
                        type="number"
                        value={counts.rare}
                        onChange={(e) => setCounts({ ...counts, rare: Math.max(parseInt(e.target.value),0)})}
                    />
                    </div>

                    <div>
                    # of Very Rare Items:
                    <input
                        type="number"
                        value={counts.veryRare}
                        onChange={(e) => setCounts({ ...counts, veryRare: Math.max(parseInt(e.target.value),0)})}
                    />
                    </div>

                    <div>
                    # of Epic Items:
                    <input
                        type="number"
                        value={counts.epic}
                        onChange={(e) => setCounts({ ...counts, epic: Math.max(parseInt(e.target.value),0)})}
                    />
                    </div>

                    <div>
                    # of Legendary Items:
                    <input
                        type="number"
                        value={counts.legendary}
                        onChange={(e) => setCounts({ ...counts, legendary: Math.max(parseInt(e.target.value),0)})}
                    />
                    </div>

                    <div className="lootmodal-last-middle-row">
                    Allow Unique Items:
                    <input
                        type="checkbox"
                        checked={uniqueAllowed}
                        onChange={(e) => setUniqueAllowed(e.target.checked)}
                    />
                    </div>
                </div>
                <div className="lootmodal-button-row">
                    <div className="lootmodal-submit-button" onClick={handleSubmit}>Submit</div>
                    <div className="lootmodal-cancel-button" onClick={onClose}>Cancel</div>
                </div>
            </div>
        </div>
    </div>
  );
};

export default LootModal;
