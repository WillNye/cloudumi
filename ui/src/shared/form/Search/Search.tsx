import { ReactNode, useCallback, useMemo, useState } from 'react';
import { Input, InputProps } from '../Input';
import { Icon } from 'shared/elements/Icon';
import styles from './Search.module.css';
import { Spinner } from '@noqdev/cloudscape';

export interface SearchProps<T> extends InputProps {
  resultRenderer: (result: T) => ReactNode;
  results?: T[];
  onResultSelect?: (result: T) => void;
  showResults?: boolean;
  isLoading?: boolean;
}

export const Search = <T,>({
  results = [],
  resultRenderer,
  onResultSelect,
  value,
  isLoading,
  ...rest
}: SearchProps<T>) => {
  const [focused, setFocused] = useState(false);
  const onFocus = useCallback(() => setFocused(true), []);
  const onBlur = useCallback(() => setFocused(false), []);

  const showResults = useMemo(() => {
    return Boolean(focused && value);
  }, [focused, value]);

  return (
    <div className={styles.container}>
      <Input
        type="search"
        placeholder="Search..."
        prefix={isLoading ? <Spinner /> : <Icon name="search" size="medium" />}
        onFocus={onFocus}
        onBlur={onBlur}
        value={value}
        {...rest}
      />
      {showResults && (
        <ul className={styles.results}>
          {results.length ? (
            results.map((result, index) => (
              <li
                key={index}
                className={styles.result}
                onClick={() => onResultSelect(result)}
              >
                {resultRenderer(result)}
              </li>
            ))
          ) : (
            <li className={styles.result}>
              <p>No Results Found</p>
            </li>
          )}
        </ul>
      )}
    </div>
  );
};
