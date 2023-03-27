import classNames from 'classnames';
import { FC, ReactNode, useMemo } from 'react';
import { Loader } from 'shared/elements/Loader';
import styles from './Segment.module.css';

interface SegmentProps {
  isLoading?: boolean;
  children: ReactNode;
}

export const Segment: FC<SegmentProps> = ({ isLoading, children }) => {
  const overLayClasses = useMemo(
    () =>
      classNames(styles.loaderOverlay, {
        [styles.disabled]: !isLoading
      }),
    [isLoading]
  );

  return (
    <div className={styles.segment}>
      <Loader className={overLayClasses} />
      {children}
    </div>
  );
};
