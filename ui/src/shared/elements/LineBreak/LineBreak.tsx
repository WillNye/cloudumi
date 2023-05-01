import styles from './LineBreak.module.css';

interface LineBreakProps {
  size?: 'small' | 'medium' | 'large';
}

export const LineBreak: React.FC<LineBreakProps> = ({ size = 'medium' }) => {
  return <div className={`${styles.lineBreak} ${styles[size]}`} />;
};
