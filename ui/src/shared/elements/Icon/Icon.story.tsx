import { Icon } from './Icon';

export default {
  title: 'Elements/Icon',
  component: Icon
};

export const Basic = () => {
  return (
    <>
      <Icon name="account-id" size="small" />
      <Icon name="pending" size="small" />
      <Icon name="signin" size="medium" />
      <Icon name="recents" size="large" />
      <Icon name="expired" size="large" />
    </>
  );
};
