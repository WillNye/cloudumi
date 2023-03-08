import _, { debounce } from 'lodash';
import { useCallback, useMemo, useState } from 'react';
import { Search } from '../Search';
import { Chip } from 'shared/elements/Chip';
import { Icon } from 'shared/elements/Icon';

export const TypeaheadBlock = ({
  handleInputUpdate,
  defaultValue,
  defaultValues,
  typeahead,
  noQuery,
  resultsFormatter,
  shouldTransformResults
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [selectedValues, setSelectedValues] = useState(defaultValues ?? []);
  const [value, setValue] = useState(defaultValue ?? '');

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
    ({ result }) => {
      const values = [...selectedValues];
      values.push(result.title);

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

        const re = new RegExp(_.escapeRegExp(value), 'i');
        const isMatch = result => re.test(result.title);

        const TYPEAHEAD_API = noQuery
          ? typeahead
          : typeahead.replace('{query}', value);
      }, 300),
    [noQuery, selectedValues, handleInputUpdate, typeahead]
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
          {selectedValue}
          <Icon
            name="close"
            onClick={() => handleSelectedValueDelete(selectedValue)}
          />
        </Chip>
      )),
    [selectedValues]
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
