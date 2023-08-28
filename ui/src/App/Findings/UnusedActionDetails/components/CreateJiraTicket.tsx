import { TextArea } from 'shared/form/TextArea';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import { Select, SelectOption } from 'shared/form/Select';
import { LineBreak } from 'shared/elements/LineBreak';
import { Segment } from 'shared/layout/Segment';
import { Button } from 'shared/elements/Button';
import styles from '../UnusedActionDetails.module.css';

const CreateJiraTicket = ({ showDialog, setShowDialog }) => {
  return (
    <Dialog
      header="Create Jira Ticket"
      setShowDialog={setShowDialog}
      showDialog={showDialog}
      size="medium"
    >
      <Segment>
        <Block disableLabelPadding label="Project" />
        <Select value="test">
          <SelectOption value="test">test</SelectOption>
        </Select>
        <LineBreak />
        <Block disableLabelPadding label="Issue Type" />
        <Select value="test">
          <SelectOption value="test">test</SelectOption>
        </Select>
        <LineBreak />
        <Block disableLabelPadding label="Department" />
        <Select value="test">
          <SelectOption value="test">test</SelectOption>
        </Select>
        <LineBreak />
        <Block disableLabelPadding label="Assignee" />
        <TextArea />
        <LineBreak />
        <Block disableLabelPadding label="Title" />
        <TextArea />
        <LineBreak />
        <div className={styles.modalActions}>
          <Button variant="outline" color="secondary" size="small">
            Cancel
          </Button>
          <Button size="small">Submit</Button>
        </div>
      </Segment>
    </Dialog>
  );
};

export default CreateJiraTicket;
