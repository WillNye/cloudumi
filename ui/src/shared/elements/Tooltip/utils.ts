import { GAP, TOOLTIP_ALIGNMENT } from './constants';

const getTopPosition = ({ targetRect, tooltipRect }) => {
  const x = targetRect.x + targetRect.width / 2 - tooltipRect.width / 2;
  const y = targetRect.y - tooltipRect.height - GAP;
  return { x, y };
};

const getRightPostion = ({ targetRect, tooltipRect }) => {
  const x = targetRect.x + targetRect.width + GAP;
  const y = targetRect.y + targetRect.height / 2 - tooltipRect.height / 2;
  return { x, y };
};

const getLeftPostion = ({ targetRect, tooltipRect }) => {
  const x = targetRect.x - tooltipRect.width - GAP;
  const y = targetRect.y + targetRect.height / 2 - tooltipRect.height / 2;
  return { x, y };
};

const getBottomPostion = ({ targetRect, tooltipRect }) => {
  const x = targetRect.x + targetRect.width / 2 - tooltipRect.width / 2;
  const y = targetRect.y + targetRect.height + GAP;
  return { x, y };
};

const TOOLTIP_POSITION_UTILS = {
  [TOOLTIP_ALIGNMENT.BOTTOM]: getBottomPostion,
  [TOOLTIP_ALIGNMENT.TOP]: getTopPosition,
  [TOOLTIP_ALIGNMENT.LEFT]: getLeftPostion,
  [TOOLTIP_ALIGNMENT.RIGHT]: getRightPostion
};

export const getTooltipPosition = ({ targetRect, tooltipRect, alignment }) => {
  return (
    TOOLTIP_POSITION_UTILS[alignment] ??
    TOOLTIP_POSITION_UTILS[TOOLTIP_ALIGNMENT.TOP]
  )({ targetRect, tooltipRect });
};
