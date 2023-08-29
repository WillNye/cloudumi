import { LineBreak } from 'shared/elements/LineBreak';
import { Checkbox } from 'shared/form/Checkbox';
import { TextArea } from 'shared/form/TextArea';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';
import { Button } from 'shared/elements/Button';
import styles from '../UnusedActionDetails.module.css';
import { useState } from 'react';

const CreateRequest = ({ showDialog, setShowDialog }) => {
  const [isEmailChecked, setIsEmailChecked] = useState(false);
  const [isTeamsChecked, setIsTeamsChecked] = useState(false);
  const [isSlackChecked, setIsSlackChecked] = useState(false);
  return (
    <Dialog
      header="Resolve with a Noq Request"
      subHeader="Before submitting the request, we need some additional information."
      setShowDialog={setShowDialog}
      showDialog={showDialog}
      size="medium"
    >
      <Segment>
        <h4>Who should be notified?</h4>
        <LineBreak />
        <div className={styles.alignContent}>
          <Checkbox
            checked={isEmailChecked}
            onChange={e => setIsEmailChecked(e.target.checked)}
          />
          <div className={styles.padLeft}>Email</div>
        </div>
        {isEmailChecked && (
          <div className={styles.padLeft}>
            <LineBreak size="small" />
            <Select value="test-1" multiple>
              <SelectOption value="test-1">test 1</SelectOption>
              <SelectOption value="test-2">test 2</SelectOption>
            </Select>
          </div>
        )}
        <LineBreak />
        <div className={styles.alignContent}>
          <Checkbox
            checked={isSlackChecked}
            onChange={e => setIsSlackChecked(e.target.checked)}
          />
          <div className={styles.padLeft}>Slack</div>
        </div>
        {isSlackChecked && (
          <div className={styles.padLeft}>
            <LineBreak size="small" />
            <Select value="test-1" multiple>
              <SelectOption value="test-1">test 1</SelectOption>
              <SelectOption value="test-2">test 2</SelectOption>
            </Select>
          </div>
        )}
        <LineBreak />
        <div className={styles.alignContent}>
          <Checkbox
            checked={isTeamsChecked}
            onChange={e => setIsTeamsChecked(e.target.checked)}
          />
          <div className={styles.padLeft}>Teams</div>
        </div>
        {isTeamsChecked && (
          <div className={styles.padLeft}>
            <LineBreak size="small" />
            <Select value="test-1" multiple>
              <SelectOption value="test-1">test 1</SelectOption>
              <SelectOption value="test-2">test 2</SelectOption>
            </Select>
          </div>
        )}
        <LineBreak size="large" />
        <Block disableLabelPadding label="Justification for request" />
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

export default CreateRequest;
