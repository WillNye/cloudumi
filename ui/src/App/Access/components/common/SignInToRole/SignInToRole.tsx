import { useState } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import AWSSignIn from '../AWSSignIn/AWSSignIn';

const SignInToRole = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { search } = useLocation();
  const roleQuery = useParams()['*'];

  const roleParams = {
    arn: roleQuery
  };

  return (
    <AWSSignIn
      role={roleParams}
      extraParams={search}
      showDialogInitially={true}
      setErrorMessage={setErrorMessage}
    />
  );
};

export default SignInToRole;
