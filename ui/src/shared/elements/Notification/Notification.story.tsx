import { Button } from '../Button';
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
      <br />
      <Notification
        type={NotificationType.INFO}
        header="New version available"
      />
      <br />
      <Notification
        type={NotificationType.INFO}
        header="New version available"
        message="An improved version of NOQ is available now, please refresh to update."
      >
        <br />
        <Button size="small">Refresh Now</Button>
      </Notification>
      <br />
      <Notification
        type={NotificationType.SUCCESS}
        header="Request submitted"
      />
      <br />
      <Notification
        type={NotificationType.SUCCESS}
        header="Request submitted"
        message="Your access request is submitted successfully."
      />
      <br />
      <Notification type={NotificationType.ERROR} header="Access declined" />
      <br />
      <Notification
        type={NotificationType.ERROR}
        header="Access declined"
        message="Your access request is declined."
      />
      <br />
      <Notification
        type={NotificationType.WARNING}
        header="Request not submitted"
      />
      <br />
      <Notification
        type={NotificationType.WARNING}
        header="Request not submitted"
        message="Your access request is not submitted."
      />
    </>
  );
};
