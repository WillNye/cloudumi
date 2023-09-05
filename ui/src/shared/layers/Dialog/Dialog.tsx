import {
  useCallback,
  ReactNode,
  Dispatch,
  useMemo,
  forwardRef,
  Ref,
  Fragment
} from 'react';
import styles from './Dialog.module.css';
import classNames from 'classnames';
import { createPortal } from 'react-dom';
import { Icon } from 'shared/elements/Icon';
import { Loader } from 'shared/elements/Loader';
import useClickOutside from 'shared/utils/hooks/useClickOutside';

interface DialogProps {
  showDialog: boolean;
  setShowDialog: Dispatch<boolean>;
  header?: ReactNode;
  subHeader?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  size?: 'small' | 'medium' | 'large' | 'fullWidth';
  disablePadding?: boolean;
  isLoading?: boolean;
  showCloseIcon?: boolean;
  disableClickOutside?: boolean;
}

export const Dialog = forwardRef(
  (
    {
      showDialog,
      setShowDialog,
      header = <Fragment />,
      subHeader,
      children,
      footer,
      size = 'fullWidth',
      disablePadding,
      isLoading,
      showCloseIcon = true,
      disableClickOutside = true
    }: DialogProps,
    ref: Ref<HTMLDivElement>
  ) => {
    const handleCloseDialog = useCallback(() => {
      if (disableClickOutside) {
        return;
      }
      setShowDialog(false);
    }, [setShowDialog, disableClickOutside]);
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
            <div className={styles.wrapper}>
              <div className={styles.overlay} onClick={handleCloseDialog} />
              <div className={dialogClasses} ref={resolvedRef}>
                <div className={styles.dialog}>
                  <div className={styles.header}>
                    <div className={styles.title}>
                      <div>{header}</div>
                      <div
                        className={styles.pointer}
                        onClick={() => setShowDialog(false)}
                      >
                        {showCloseIcon && <Icon name="close" size="large" />}
                      </div>
                    </div>
                    {subHeader && (
                      <h4 className={styles.subTitle}>{subHeader}</h4>
                    )}
                  </div>
                  {isLoading ? (
                    <div className={styles.loader}>
                      <div>
                        <Loader />
                      </div>
                    </div>
                  ) : (
                    children
                  )}
                  <span>{footer}</span>
                </div>
              </div>
            </div>,
            document.body
          )}
      </>
    );
  }
);
