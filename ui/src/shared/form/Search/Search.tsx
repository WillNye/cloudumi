import {
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import { Input, InputProps } from '../Input';
import { Icon } from 'shared/elements/Icon';
import styles from './Search.module.css';
import { Spinner } from '@noqdev/cloudscape';
import useClickOutside from 'shared/utils/hooks/useClickOutside';

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

  const containerRef = useClickOutside(onBlur);

  // const containerRef = useRef(null);
  const contentRef = useRef(null);

  const showResults = useMemo(() => {
    return Boolean(focused && value);
  }, [focused, value]);

  useEffect(() => {
    if (!contentRef.current) {
      return;
    }

    if (results?.length) {
      const dropdownMenu = contentRef.current;
      const contentHeight = dropdownMenu.scrollHeight + 10;
      const maxHeight =
        window.innerHeight - dropdownMenu.getBoundingClientRect().top - 100;
      dropdownMenu.style.maxHeight = `${Math.min(contentHeight, maxHeight)}px`;
    } else {
      contentRef.current.style.maxHeight = '80px';
    }
  }, [results, contentRef, focused]);

  return (
    <div className={styles.container} ref={containerRef}>
      <Input
        type="search"
        placeholder="Search..."
        prefix={<Icon name="search" size="medium" />}
        onFocus={onFocus}
        value={value}
        {...rest}
      />
      {showResults && (
        <ul className={styles.results} ref={contentRef}>
          {isLoading ? (
            <li className={styles.noResults}>
              <Spinner />
            </li>
          ) : results.length ? (
            results.map((result, index) => (
              <li
                key={index}
                className={styles.result}
                onClick={() => {
                  onResultSelect?.(result);
                  onBlur();
                }}
              >
                {resultRenderer(result)}
              </li>
            ))
          ) : (
            <li className={styles.noResults}>
              <p>No Results Found</p>
            </li>
          )}
        </ul>
      )}
    </div>
  );
};
