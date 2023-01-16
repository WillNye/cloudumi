import { useRef, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Divider } from 'shared/elements/Divider';
import { List, ListItem } from 'shared/layout/List';
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
      <Button type="button" ref={buttonRef} onClick={() => setOpen(!open)}>
        Open
      </Button>
      <Menu open={open} onClose={() => setOpen(false)} reference={buttonRef}>
        <ul>
          <li>Item1</li>
          <li>Item2</li>
          <li>Item3</li>
        </ul>
      </Menu>
    </>
  );
};

export const Lists = () => {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);

  return (
    <>
      <Button type="button" ref={buttonRef} onClick={() => setOpen(!open)}>
        Open
      </Button>
      <Menu open={open} onClose={() => setOpen(false)} reference={buttonRef}>
        <List>
          <ListItem>Item1</ListItem>
          <ListItem>Item2</ListItem>
          <Divider />
          <ListItem>Item3</ListItem>
        </List>
      </Menu>
    </>
  );
};
