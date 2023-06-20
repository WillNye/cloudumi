import _, { debounce } from 'lodash';
import { ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import { Search } from '../Search';
import { Chip } from 'shared/elements/Chip';
import { Icon } from 'shared/elements/Icon';
import axios from 'core/Axios/Axios';

interface TypeaheadBlockProps {
  handleOnSelectResult?: (value: string) => void;
  handleOnRemoveValue?: (value: string) => void;
  handleOnChange?: (value: string) => void;
  defaultValue?: string;
  defaultValues?: any[];
  resultsFormatter: (result: any) => ReactNode;
  endpoint: string;
  queryParam: string;
  titleKey?: string;
}

export const TypeaheadBlock = ({
  handleOnChange,
  handleOnSelectResult,
  handleOnRemoveValue,
  defaultValue,
  defaultValues,
  resultsFormatter,
  endpoint,
  queryParam,
  titleKey = 'title'
}: TypeaheadBlockProps) => {
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
        handleOnSelectResult?.(e.target.value);
      }
    },
    [handleOnSelectResult, selectedValues]
  );

  const handleSelectedValueDelete = useCallback(
    value => {
      const values = selectedValues?.filter(item => item !== value);
      setSelectedValues(values);
      handleOnRemoveValue?.(value);
    },
    [selectedValues, handleOnRemoveValue]
  );

  const handleResultSelect = useCallback(
    result => {
      const values = [...selectedValues];
      values.push(result);

      setSelectedValues(values);

      handleOnSelectResult?.(result);
    },
    [selectedValues, handleOnSelectResult]
  );

  const debouncedSearchFilter = useMemo(
    () =>
      debounce(value => {
        setIsLoading(true);

        if (value.length < 1) {
          setIsLoading(false);
          setResults([]);
          setValue('');
          handleOnChange?.('');
          return;
        }
      }, 300),
    [handleOnChange]
  );

  const handleSearchChange = useCallback(
    e => {
      e.preventDefault();
      const newValue = e.target.value;
      setValue(newValue);

      handleOnChange?.(newValue);
      debouncedSearchFilter(newValue);
    },
    [debouncedSearchFilter, handleOnChange]
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
    [selectedValues, handleSelectedValueDelete, titleKey]
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
