import React, { useRef, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Menu } from './Menu';

export default {
  title: 'Layers/Menu',
  component: Menu
};

export const Simple = () => {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);

  return (
    <>
      <Button
        type="button"
        ref={buttonRef}
        onClick={() => setOpen(!open)}
      >
        Open
      </Button>
      <Menu
        open={open}
        onClose={() => setOpen(false)}
        reference={buttonRef}
      >
        <ul>
          <li>Item1</li>
          <li>Item2</li>
          <li>Item3</li>
        </ul>
      </Menu>
    </>
  );
};
