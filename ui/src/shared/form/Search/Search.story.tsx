import { useCallback, useEffect, useRef, useState } from 'react';
import { Search } from './Search';
import filter from 'lodash/filter';
import escapeRegExp from 'lodash/escapeRegExp';
import { data } from './data';

export default {
  title: 'Form/Search',
  component: Search
};

export const Basic = () => {
  const [value, setValue] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const timeoutRef = useRef();

  const handleSearchChange = useCallback(e => {
    setIsLoading(true);
    e.preventDefault();
    const newValue = e.target.value;
    setValue(newValue);

    clearTimeout(timeoutRef.current);
    // @ts-ignore
    timeoutRef.current = setTimeout(() => {
      if (newValue.length === 0) {
        setResults([]);
        setIsLoading(false);
        return;
      }

      const re = new RegExp(escapeRegExp(newValue), 'i');
      const isMatch = result => re.test(result.title);
      setResults(data.filter(item => isMatch(item)));
      setIsLoading(false);
    }, 1000);
  }, []);

  const resultRenderer = result => <p>{result.title}</p>;

  useEffect(() => {
    return () => {
      clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <Search
      value={value}
      results={results}
      onChange={handleSearchChange}
      isLoading={isLoading}
      resultRenderer={resultRenderer}
    />
  );
};
