import { Card } from 'reablocks';
import { LineBreak } from 'shared/elements/LineBreak';
import { Segment } from 'shared/layout/Segment';

const SelectRequestType = () => {
  return (
    <Segment>
      <h3>Request Access</h3>
      <p>What would you like to do?</p>
      <LineBreak />
      <Card></Card>
    </Segment>
  );
};

export default SelectRequestType;
