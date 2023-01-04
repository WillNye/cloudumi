import { Notification } from './Notification';

export default {
  title: 'Elements/Notification',
  component: Notification
};

export const Basic = () => {
  return (
    <>
      <Notification message="This is a left tooltip">
        <div>Left</div>
      </Notification>
      <br />
      <Notification message="This is a right tooltip">
        <div>Right</div>
      </Notification>
      <br />
      <Notification message="This is a bottom tooltip">
        <div>Bottom</div>
      </Notification>
      <br />
      <Notification message="This is a top tooltip">Top</Notification>
    </>
  );
};
