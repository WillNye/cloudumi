import { useMemo } from 'react';
import classNames from 'classnames';
import styles from './HorizontalStepper.module.css';

const Step = ({ id, header, subHeader, activeId }) => {
  const classes = useMemo(
    () =>
      classNames({
        [styles.complete]: activeId > id,
        [styles.active]: activeId === id
      }),
    [activeId, id]
  );

  return (
    <li className={`${styles.item} ${classes}`}>
      <span className={styles.label}>{id}</span>
      <h3 className={styles.title}>{header}</h3>
      <p className={styles.desc}>{subHeader}</p>
    </li>
  );
};

const HorizontalStepper = ({ steps, activeId }) => {
  return (
    <div className={styles.wrapper}>
      <ol className={styles.stepper}>
        {steps.map((step, index) => (
          <Step {...step} activeId={activeId} key={index} />
        ))}
      </ol>
      <br />
    </div>
  );
};

export default HorizontalStepper;
