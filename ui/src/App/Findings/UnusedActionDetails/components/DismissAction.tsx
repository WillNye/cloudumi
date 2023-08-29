import { Button } from 'shared/elements/Button';
import { LineBreak } from 'shared/elements/LineBreak';
import { Radio } from 'shared/form/Radio';
import { TextArea } from 'shared/form/TextArea';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import { Segment } from 'shared/layout/Segment';
import styles from '../UnusedActionDetails.module.css';

const DismissAction = ({ showDialog, setShowDialog }) => {
  return (
    <Dialog
      header="Dismiss All Findings on MonitoringServiceRole"
      setShowDialog={setShowDialog}
      showDialog={showDialog}
      size="medium"
    >
      <Segment>
        <h4>For how long</h4>
        <LineBreak />
        <div className={styles.alignContent}>
          <Radio />
          <div className={styles.padLeft}>For a certain amount of time</div>
        </div>
        <LineBreak size="small" />
        <div className={styles.alignContent}>
          <Radio />
          <div className={styles.padLeft}>Forever</div>
        </div>
        <LineBreak />
        <Block disableLabelPadding label="Justification" />
        <TextArea />
        <LineBreak />
        <div className={styles.modalActions}>
          <Button variant="outline" color="secondary" size="small">
            Cancel
          </Button>
          <Button size="small">Dismiss</Button>
        </div>
      </Segment>
    </Dialog>
  );
};

export default DismissAction;
