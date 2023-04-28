import React, { FC } from 'react';
import classNames from 'classnames';
import styles from './SectionHeader.module.css';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  size?: 'small' | 'medium' | 'large';
  border?: boolean;
  shadow?: boolean;
  className?: string;
}

const SectionHeader: FC<SectionHeaderProps> = ({
  title,
  subtitle,
  size = 'medium',
  border = false,
  shadow = false,
  className
}) => {
  const titleSizeClass = classNames({
    [styles.title]: true,
    [styles.titleSmall]: size === 'small',
    [styles.titleMedium]: size === 'medium',
    [styles.titleLarge]: size === 'large'
  });

  const sectionHeaderClass = classNames({
    [styles.sectionHeader]: true,
    [styles.sectionHeaderBorder]: border,
    [styles.sectionHeaderShadow]: shadow,
    [className]: className
  });

  return (
    <div className={sectionHeaderClass}>
      <div className={titleSizeClass}>{title}</div>
      {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
    </div>
  );
};

export default SectionHeader;
