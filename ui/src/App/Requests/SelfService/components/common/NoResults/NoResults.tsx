import styles from './NoResult.module.css';
import noResultsImg from '../../../../../assets/illustrations/empty.svg';
import { LineBreak } from 'shared/elements/LineBreak';

type NoResultsProps = {
  title?: string;
  description?: string;
};

const NoResults = () => {
  return (
    <div className={styles.container}>
      <img src={noResultsImg} />
      <LineBreak />
      <h3>No Choices Found for Selected Option</h3>
      <h5 className={styles.text}>
        No Choices Found: We apologize for the inconvenience, but it seems that
        there are no choices available for the selected type at the moment. Rest
        assured, our team is working diligently to update the options as soon as
        possible. Should you need any further information or guidance, feel free
        to contact our dedicated support team who will gladly assist you.
      </h5>
    </div>
  );
};

export default NoResults;
