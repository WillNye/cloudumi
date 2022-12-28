import React from 'react';
import styles from './Checkbox.module.css';

export const Checkbox = ({ label, isSelected, onCheckboxChange, toggle }) => (
  <div className="form-check">
    <label>
      <input
        type="checkbox"
        checked={isSelected}
        onChange={onCheckboxChange}
        className="form-check-input"
      />
      {label}
    </label>
  </div>
);
