import { useState, useRef } from 'react';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';
import { Menu } from 'shared/layers/Menu';

const MoreActions = () => {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);

  return (
    <>
      <div ref={buttonRef} onClick={() => setOpen(!open)}>
        <Icon name="more" size="large" color="secondary" />
      </div>
      <Menu open={open} onClose={() => setOpen(false)} reference={buttonRef}>
        <div>
          <Button variant="text" color="secondary" size="small" fullWidth>
            Add Permissions
          </Button>
          <Button variant="text" color="secondary" size="small" fullWidth>
            View Details
          </Button>
        </div>
      </Menu>
    </>
  );
};

export default MoreActions;
