import { Divider } from 'shared/elements/Divider';
import styles from './SidePanel.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';

export const SidePanel = () => {
  const { selfServiceRequest } = useContext(SelfServiceContext).store;
  return (
    <div className={styles.sidepanel}>
      <h4>Details</h4>
      <Divider orientation="horizontal" />
      <LineBreak />
      <div>
        <p className={styles.header}>Cloud Provider</p>
        <p>{selfServiceRequest.provider}</p>
      </div>
      <LineBreak />
      {selfServiceRequest?.requestType && (
        <>
          <p className={styles.header}>Need</p>
          <p>{selfServiceRequest?.requestType?.name}</p>
        </>
      )}

      {selfServiceRequest?.identity && (
        <>
          <LineBreak />
          <p className={styles.header}>Identity</p>
          <p>{selfServiceRequest?.identity?.template_type}</p>
        </>
      )}

      {selfServiceRequest?.changeType && (
        <>
          <LineBreak />
          <p className={styles.header}>Need</p>
          <p>{selfServiceRequest?.changeType?.name}</p>
        </>
      )}
    </div>
  );
};

export default SidePanel;
