import { useState } from 'react';
import { useParams } from 'react-router-dom';
import AWSSignIn from '../AWSSignIn/AWSSignIn';

const SignInToRole = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const roleQuery = useParams()['*'];

  const roleParams = {
    arn: roleQuery
  };

  return (
    <AWSSignIn
      role={roleParams}
      showDialogInitially={true}
      setErrorMessage={setErrorMessage}
    />
  );
};

export default SignInToRole;
