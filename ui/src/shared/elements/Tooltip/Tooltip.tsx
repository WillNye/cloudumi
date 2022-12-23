import classNames from 'classnames';
import { useCallback, useEffect, useRef, useState } from 'react';
import styles from './Tooltip.module.css';
import { getTooltipPosition } from './utils';

export interface TooltipProps
  extends Omit<
    React.HTMLAttributes<HTMLDivElement>,
    'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag'
  > {
  alignment?: 'top' | 'bottom' | 'left' | 'right';
  disabled?: boolean;
  text: string;
}

export const Tooltip = ({
  children,
  text,
  alignment = 'top',
  disabled = false
}: TooltipProps) => {
  const tooltipRef = useRef(null);
  const targetRef = useRef(null);
  const [tooltipRect, setTooltipRect] = useState(null);
  const [targetRect, setTargetRect] = useState(null);

  const [shown, setShown] = useState(false);

  const classes = classNames(styles.tooltipText, {
    [styles[alignment]]: alignment,
    [styles.disabled]: disabled,
    [styles.shown]: shown
  });

  useEffect(
    function onTooltipShown() {
      setTooltipRect(tooltipRef.current.getBoundingClientRect());
      setTargetRect(targetRef.current.getBoundingClientRect());
    },
    [shown]
  );

  const setPosition = useCallback(
    ({ x, y }) => {
      x = Math.round(x);
      y = Math.round(y);
      tooltipRef.current.style = `left: ${x}px; top: ${y}px;`;
    },
    [tooltipRef]
  );

  useEffect(
    function calculateTooltipPosition() {
      if (shown) {
        const tooltipPosition = getTooltipPosition({
          tooltipRect,
          targetRect,
          alignment
        });
        setPosition(tooltipPosition);
      }
    },
    [tooltipRect, targetRect, alignment, setPosition, shown]
  );

  const showTooltip = useCallback(() => {
    if (!disabled) {
      setShown(true);
    }
  }, [disabled, setShown]);

  const hideTooltip = useCallback(() => {
    if (!disabled) {
      setShown(false);
    }
  }, [disabled, setShown]);

  return (
    <span
      className={styles.tooltip}
      ref={targetRef}
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
    >
      {children}
      <div ref={tooltipRef} className={classes}>
        {text}
      </div>
    </span>
  );
};
