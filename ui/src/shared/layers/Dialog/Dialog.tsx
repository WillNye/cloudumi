import {
  useEffect,
  useCallback,
  useRef,
  ReactNode,
  Dispatch,
  useMemo,
  forwardRef,
  Ref
} from 'react';
import styles from './Dialog.module.css';
import classNames from 'classnames';
import { createPortal } from 'react-dom';
import { Icon } from 'shared/elements/Icon';

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

export const Dialog = forwardRef(
  (
    {
      showDialog,
      setShowDialog,
      header,
      children,
      footer,
      size = 'fullWidth',
      disablePadding
    }: DialogProps,
    ref: Ref<HTMLDivElement>
  ) => {
    const handleCloseDialog = useCallback(
      () => setShowDialog(false),
      [setShowDialog]
    );
    const dialogRef = useClickOutside(handleCloseDialog);
    const resolvedRef = useMemo(() => ref ?? dialogRef, [ref, dialogRef]);

    const dialogClasses = useMemo(
      () =>
        classNames(styles.dialogContainer, {
          [styles[size]]: size,
          [styles.disablePadding]: disablePadding
        }),
      [size, disablePadding]
    );

    return (
      <>
        {showDialog &&
          createPortal(
            <>
              <div className={styles.overlay} onClick={handleCloseDialog} />
              <div className={dialogClasses} ref={resolvedRef}>
                <div className={styles.dialog}>
                  <div className={styles.header}>
                    {header && <div>{header}</div>}
                    <div
                      className={styles.pointer}
                      onClick={() => setShowDialog(false)}
                    >
                      <Icon name="close" size="large" />
                    </div>
                  </div>
                  {children}
                  <span>{footer}</span>
                </div>
              </div>
            </>,
            document.body
          )}
      </>
    );
  }
);
