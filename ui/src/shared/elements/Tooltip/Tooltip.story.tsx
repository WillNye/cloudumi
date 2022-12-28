import { useState } from 'react';
import { Tooltip } from './Tooltip';

export default {
  title: 'Elements/Tooltip',
  component: Tooltip
};

export const Basic = () => {
  return (
    <>
      <Tooltip text="This is a left tooltip" alignment="left">
        <div>Left</div>
      </Tooltip>
      <br />
      <Tooltip text="This is a right tooltip" alignment="right">
        <div>Right</div>
      </Tooltip>
      <br />
      <Tooltip text="This is a bottom tooltip" alignment="bottom">
        <div>Bottom</div>
      </Tooltip>
      <br />
      <Tooltip text="This is a top tooltip" alignment="top">
        Top
      </Tooltip>
    </>
  );
};
