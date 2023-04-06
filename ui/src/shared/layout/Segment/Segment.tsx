import classNames from 'classnames';
import { FC, ReactNode, useMemo } from 'react';
import { Loader } from 'shared/elements/Loader';
import styles from './Segment.module.css';

interface SegmentProps extends React.HTMLAttributes<HTMLDivElement> {
  isLoading?: boolean;
  children?: ReactNode;
  disablePadding?: boolean;
}

export const Segment: FC<SegmentProps> = ({
  isLoading,
  children,
  className,
  disablePadding
}) => {
  const overLayClasses = useMemo(
    () =>
      classNames(styles.loaderOverlay, {
        [styles.disabled]: !isLoading
      }),
    [isLoading]
  );

  const segmentClasses = useMemo(
    () =>
      classNames(styles.segment, className, {
        [styles.disablePadding]: disablePadding
      }),
    [disablePadding, className]
  );

  return (
    <div className={segmentClasses}>
      <Loader className={overLayClasses} />
      <div className={styles.content}>{children}</div>
    </div>
  );
};
