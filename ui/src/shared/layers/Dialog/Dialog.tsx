import {
  useEffect,
  useCallback,
  useRef,
  ReactNode,
  Dispatch,
  useMemo
} from 'react';
import styles from './Dialog.module.css';
import classNames from 'classnames';

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

interface DialogProps {
  showDialog: boolean;
  setShowDialog: Dispatch<boolean>;
  header?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  size?: 'small' | 'medium' | 'large' | 'fullWidth';
  disablePadding?: boolean;
}

export const Dialog = ({
  showDialog,
  setShowDialog,
  header,
  children,
  footer,
  size = 'fullWidth',
  disablePadding
}: DialogProps) => {
  useEffect(() => {
    if (showDialog) {
      document.getElementById('root').style.overflow = 'hidden';
    } else {
      document.getElementById('root').style.overflow = 'auto';
    }

    return () => {
      document.getElementById('root').style.overflow = 'auto';
    };
  }, [showDialog]);

  const handleCloseDialog = useCallback(
    () => setShowDialog(false),
    [setShowDialog]
  );
  const dialogRef = useClickOutside(handleCloseDialog);

  const dialogClases = useMemo(
    () =>
      classNames(styles.dialogContainer, {
        [styles[size]]: size,
        [styles.disablePadding]: disablePadding
      }),
    [size, disablePadding]
  );

  return (
    <>
      {showDialog && (
        <>
          <div className={styles.overlay} onClick={handleCloseDialog} />
          <div className={dialogClases} ref={dialogRef}>
            <div className={styles.dialog}>
              <span>{header}</span>
              {children}
              <span>{footer}</span>
            </div>
          </div>
        </>
      )}
    </>
  );
};
