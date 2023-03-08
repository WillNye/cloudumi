import { useCallback, useEffect, useRef } from 'react';

const useClickOutside = callback => {
  const ref = useRef(null);

  const handleClick = useCallback(
    event => {
      if (ref.current && !ref.current.contains(event.target)) {
        callback();
      }
    },
    [ref, callback]
  );

  useEffect(() => {
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [handleClick]);

  return ref;
};

export default useClickOutside;
