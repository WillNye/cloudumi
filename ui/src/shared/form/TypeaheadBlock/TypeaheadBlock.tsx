import _, { debounce } from 'lodash';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Search } from '../Search';
import { Chip } from 'shared/elements/Chip';
import { Icon } from 'shared/elements/Icon';
import axios from 'core/Axios/Axios';

export const TypeaheadBlock = ({
  handleInputUpdate,
  defaultValue,
  defaultValues,
  resultsFormatter,
  endpoint,
  queryParam,
  titleKey = 'title'
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [selectedValues, setSelectedValues] = useState(defaultValues ?? []);
  const [value, setValue] = useState(defaultValue ?? '');
  const [error, setError] = useState(null);

  const fetchData = async query => {
    setIsLoading(true);
    try {
      if (!endpoint.startsWith('/')) {
        endpoint = `/${endpoint}`;
      }
      const response = await axios.get(endpoint, {
        params: {
          [queryParam]: query
        }
      });
      let data = response.data.data;
      // if data is just a list of strings, replace with objects with title
      if (data.length > 0 && typeof data[0] === 'string') {
        data = data.map(item => ({ title: item }));
      }
      setResults(data);
      setIsLoading(false);
    } catch (error) {
      setError(error);
      setIsLoading(false);
    }
  };

  const debouncedFetchData = useMemo(
    () => debounce(fetchData, 300),
    [endpoint, queryParam]
  );

  useEffect(() => {
    if (value && endpoint && queryParam) {
      debouncedFetchData(value);
    }
  }, [endpoint, queryParam, value, debouncedFetchData]);

  useEffect(() => {
    setValue(defaultValue);
    setSelectedValues(defaultValues);
  }, [defaultValue, defaultValues]);

  useEffect(() => {
    if (value) {
      debouncedFetchData(value);
    } else {
      setResults([]);
    }
  }, [value, debouncedFetchData]);

  const handleKeyDown = useCallback(
    e => {
      if (e.key === 'Enter') {
        if (!e.target.value) {
          return;
        }
        const values = [...selectedValues];
        values.push(e.target.value);
        setSelectedValues(values);
        setResults([]);
        setValue('');
        handleInputUpdate(values);
      }
    },
    [handleInputUpdate, selectedValues]
  );

  const handleSelectedValueDelete = useCallback(
    value => {
      const values = selectedValues?.filter(item => item !== value);
      setSelectedValues(values);
      handleInputUpdate(values);
    },
    [selectedValues, handleInputUpdate]
  );

  const handleResultSelect = useCallback(
    result => {
      const values = [...selectedValues];
      values.push(result);

      setSelectedValues(values);

      handleInputUpdate(values);
    },
    [selectedValues, handleInputUpdate]
  );

  const debouncedSearchFilter = useMemo(
    () =>
      debounce(value => {
        setIsLoading(true);

        if (value.length < 1) {
          setIsLoading(false);
          setResults([]);
          setValue('');
          handleInputUpdate(selectedValues);
          return;
        }
      }, 300),
    [selectedValues, handleInputUpdate]
  );

  const handleSearchChange = useCallback(
    e => {
      e.preventDefault();
      const newValue = e.target.value;
      setValue(newValue);

      handleInputUpdate(selectedValues);
      debouncedSearchFilter(newValue);
    },
    [selectedValues, debouncedSearchFilter, handleInputUpdate]
  );

  const selectedValueLabels = useMemo(
    () =>
      selectedValues.map((selectedValue, index) => (
        <Chip key={index}>
          {selectedValue[titleKey]}
          <Icon
            name="close"
            onClick={() => handleSelectedValueDelete(selectedValue)}
          />
        </Chip>
      )),
    [selectedValues, handleSelectedValueDelete]
  );

  return (
    <div>
      <Search
        isLoading={isLoading}
        onResultSelect={handleResultSelect}
        onChange={_.debounce(handleSearchChange, 500, {
          leading: true
        })}
        resultRenderer={resultsFormatter}
        onKeyDown={handleKeyDown}
        results={results}
        value={value}
      />
      <div>{selectedValueLabels}</div>
    </div>
  );
};
