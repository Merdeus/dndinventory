import React, { useState } from 'react';

const TextInputModal = ({ isOpen, onClose, onSubmit }) => {
  const [inputValue, setInputValue] = useState('');

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  const handleSubmit = () => {
    onSubmit(inputValue);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <h2 style={styles.h2}>Password required</h2>
        <p>Please enter the dm password</p>
        <input
          type="password"
          value={inputValue}
          onChange={handleInputChange}
          style={styles.input}
        />
        <div style={styles.buttons}>
          <div style={styles.oi} onClick={handleSubmit}>Submit</div>
          <div style={styles.oi} onClick={onClose}>Cancel</div>
        </div>
      </div>
    </div>
  );
};

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modal: {
    backgroundColor: '#fff',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 0 10px rgba(0, 0, 0, 0.1)',
    textAlign: 'center',
  },
  input: {
    margin: '10px 0',
    marginTop: '0px',
    marginBottom: '12px',
    padding: '8px',
    width: '100%',
    boxSizing: 'border-box',
  },
  buttons: {
    display: 'flex',
    justifyContent: 'space-between',
  },
  h2: {
    margin: 5,
  },
  oi : {
    backgroundColor: '#978686',
    color : 'white',
    padding: '6px',
    cursor: 'pointer',
  }
};

export default TextInputModal;