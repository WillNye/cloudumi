import { Link } from 'react-router-dom';
import { Button } from 'shared/elements/Button';

const AWSProvider = () => {
  return (
    <div>
      <div>
        <Link to="/settings/integrations/aws">Click Here</Link> to add a new AWS
        Account
      </div>

      <br />
      <br />
      <pre>TODO: Fetch all spoke and hub accounts</pre>
    </div>
  );
};

export default AWSProvider;
