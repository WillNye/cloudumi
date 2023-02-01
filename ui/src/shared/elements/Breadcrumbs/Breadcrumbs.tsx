import React from 'react';
import styles from './Breadcrumbs.module.css';
import { Link } from 'react-router-dom';
import { Icon } from '../Icon';

interface Breadcrumb {
  name: string;
  url: string;
}

interface Props {
  items: Breadcrumb[];
}

export const Breadcrumbs: React.FC<Props> = ({ items }) => {
  return (
    <div className={styles.breadcrumbs}>
      {items.map((item, index) => {
        const isLastElement = index === items.length - 1;
        return (
          <React.Fragment key={index}>
            <Link
              to={item.url}
              className={`${styles.breadcrumbLink} ${
                isLastElement ? styles.active : ''
              }`}
            >
              {item.name}
            </Link>
            {!isLastElement && (
              <span className={styles.divider}>
                <Icon name="chevron-right" size="large" />
              </span>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
