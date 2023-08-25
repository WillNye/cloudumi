import React, { useState, useRef, useEffect, useCallback } from 'react';
import styles from './Accordion.module.css';
import classNames from 'classnames';
import { Segment } from 'shared/layout/Segment';

interface AccordionProps {
  title: string;
  children: React.ReactNode;
}

const Accordion: React.FC<AccordionProps> = ({ title, children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.style.maxHeight = isOpen
        ? `${contentRef.current.scrollHeight}px`
        : '0px';
    }
  }, [isOpen]);

  const toggleAccordion = useCallback(() => {
    setIsOpen(open => !open);
  }, []);

  return (
    <div className={styles.accordion}>
      <button
        className={classNames(styles.accordionTitle, { [styles.open]: isOpen })}
        onClick={toggleAccordion}
      >
        {title}
      </button>
      <div ref={contentRef} className={styles.accordionContent}>
        <Segment>{children}</Segment>
      </div>
    </div>
  );
};

export default Accordion;
