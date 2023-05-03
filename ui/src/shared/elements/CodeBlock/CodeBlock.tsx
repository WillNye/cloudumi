import { useCallback, useRef, useState } from 'react';
import styles from './CodeBlock.module.css';
import { Button } from '../Button';

export const CodeBlock = ({ children }) => {
  const [isCopied, setIsCopied] = useState(false);
  const [showCopy, setShowCopy] = useState(false);

  const codeRef = useRef(null);

  const handleMouseLeave = useCallback(() => {
    setTimeout(() => {
      setIsCopied(false);
    }, 1000);
  }, []);

  const handleClick = useCallback(async () => {
    if (!codeRef?.current || !navigator?.clipboard) {
      return;
    }
    try {
      const text = codeRef.current.innerText;
      await navigator.clipboard.writeText(text);
      setIsCopied(true);
      handleMouseLeave();
    } catch (error) {
      console.warn('Copy failed', error);
      setIsCopied(false);
    }
  }, [codeRef, handleMouseLeave]);

  return (
    <div
      className={styles.codeBlock}
      onMouseEnter={() => setShowCopy(true)}
      onMouseLeave={() => setShowCopy(false)}
    >
      {showCopy && (
        <div className={styles.copyBtn}>
          <Button
            className={styles.button}
            onClick={handleClick}
            disabled={isCopied}
            icon={isCopied ? 'tick' : 'copy'}
            color={isCopied ? 'primary' : 'secondary'}
            size="small"
          />
        </div>
      )}
      <pre>
        <code ref={codeRef}>{children}</code>
      </pre>
    </div>
  );
};
