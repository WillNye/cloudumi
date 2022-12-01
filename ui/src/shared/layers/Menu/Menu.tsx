import { FC } from 'react';
import { Menu as ReaLayersMenu, MenuProps } from 'realayers';
import { Card } from 'shared/layout/Card';
import css from './Menu.module.css';

export const Menu: FC<Partial<MenuProps>> = ({
  children,
  ...rest
}) => (
  <ReaLayersMenu {...rest}>
    <Card className={css.card}>
      {children}
    </Card>
  </ReaLayersMenu>
);

Menu.defaultProps = {
  modifiers: {
    offset: {
      offset: '-3, 3'
    }
  }
};
