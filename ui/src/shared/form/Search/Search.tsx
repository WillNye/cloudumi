import React, { useState } from 'react';
import styles from './Search.module.css';
import { Input } from '../Input';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';

export const Search = ({ onSearch }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const handleChange = event => {
    setSearchTerm(event.target.value);
  };

  const handleSubmit = event => {
    event.preventDefault();
    onSearch(searchTerm);
  };

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <Input
        type="search"
        value={searchTerm}
        onChange={handleChange}
        placeholder="Search..."
        fullWidth
        suffix={<Icon name="search" size="large" />}
      />
    </form>
  );
};
