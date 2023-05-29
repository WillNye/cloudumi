import { Button } from '../Button';
import { LineBreak } from '../LineBreak';
import { Notification, NotificationType } from './Notification';

export default {
  title: 'Elements/Notification',
  component: Notification
};

export const Basic = () => {
  return (
    <>
      <Notification
        header="Are you sure you want to delete this request?"
        message="This action cannot be reversed."
      />
      <LineBreak />
      <Notification
        type={NotificationType.INFO}
        header="New version available"
      />
      <LineBreak />
      <Notification
        type={NotificationType.INFO}
        header="New version available"
        message="An improved version of NOQ is available now, please refresh to update."
      >
        <LineBreak />
        <Button size="small">Refresh Now</Button>
      </Notification>
      <LineBreak />
      <Notification
        type={NotificationType.SUCCESS}
        header="Request submitted"
      />
      <LineBreak />
      <Notification
        type={NotificationType.SUCCESS}
        header="Request submitted"
        message="Your access request is submitted successfully."
      />
      <LineBreak />
      <Notification type={NotificationType.ERROR} header="Access declined" />
      <LineBreak />
      <Notification
        type={NotificationType.ERROR}
        header="Access declined"
        message="Your access request is declined."
      />
      <LineBreak />
      <Notification
        type={NotificationType.WARNING}
        header="Request not submitted"
      />
      <LineBreak />
      <Notification
        type={NotificationType.WARNING}
        header="Request not submitted"
        message="Your access request is not submitted."
      />
    </>
  );
};
