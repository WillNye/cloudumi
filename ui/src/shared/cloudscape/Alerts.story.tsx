import React from 'react';
import Alert from '@noqdev/cloudscape/alert';
import Button from '@noqdev/cloudscape/button';

export default {
  title: 'Cloudscape/Alerts',
  component: Alert
};

export const InfoAlert = () => {
  const [visible, setVisible] = React.useState(true);
  return (
    <Alert
      onDismiss={() => setVisible(false)}
      visible={visible}
      dismissAriaLabel="Close alert"
      header="Known issues/limitations"
    >
      Review the documentation to learn about potential compatibility issues
      with specific database versions.
    </Alert>
  );
};

export const SuccessAlert = () => {
  const [visible, setVisible] = React.useState(true);
  return (
    <Alert
      onDismiss={() => setVisible(false)}
      visible={visible}
      dismissAriaLabel="Close alert"
      dismissible
      type="success"
    >
      Your instance has been created successfully.
    </Alert>
  );
};

export const ErrorAlert = () => {
  const [visible, setVisible] = React.useState(true);
  return (
    <Alert
      onDismiss={() => setVisible(false)}
      visible={visible}
      dismissAriaLabel="Close alert"
      type="error"
      header="Your instances could not be stopped"
    >
      Remove the instance from the load balancer before stopping it.
    </Alert>
  );
};

export const AlertWarning = () => {
  const [visible, setVisible] = React.useState(true);
  return (
    <Alert
      onDismiss={() => setVisible(false)}
      visible={visible}
      dismissAriaLabel="Close alert"
      type="warning"
    >
      Changing the configuration might require stopping the instance.
    </Alert>
  );
};

export const AlertWithButton = () => {
  const [visible, setVisible] = React.useState(true);
  return (
    <Alert
      onDismiss={() => setVisible(false)}
      visible={visible}
      dismissAriaLabel="Close alert"
      action={<Button>Enable versioning</Button>}
      header="Versioning is not enabled"
    >
      Versioning is not enabled for objects in bucket [IAM-user].
    </Alert>
  );
};
