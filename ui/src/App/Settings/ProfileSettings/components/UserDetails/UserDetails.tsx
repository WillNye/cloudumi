import { useAuth } from 'core/Auth';
import { Avatar } from 'shared/elements/Avatar';
import { Segment } from 'shared/layout/Segment';
import { Card } from 'shared/layout/Card';
import { LineBreak } from 'shared/elements/LineBreak';

const UserDetails = () => {
  const { user } = useAuth();
  return (
    <Segment>
      <Card>
        <div>
          <Avatar name={user.user} size="large" />
          <LineBreak size="small" />
          <div>{user.user}</div>
        </div>
      </Card>
      <LineBreak />
      <Card header="My Groups"></Card>
      <LineBreak />
      <Card header="My Requests"></Card>
    </Segment>
  );
};

export default UserDetails;
