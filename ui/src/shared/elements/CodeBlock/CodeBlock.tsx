import { FC, ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import styles from './CodeBlock.module.css';
import { Button } from '../Button';
import Prism from 'prismjs';
import 'prismjs/themes/prism-dark.css';
import classNames from 'classnames';

interface CodeBlockProps {
  code: ReactNode;
  language?: string;
}

export const CodeBlock: FC<CodeBlockProps> = ({
  code,
  language = 'powershell'
}) => {
  const codeRef = useRef(null);

  const [isCopied, setIsCopied] = useState(false);
  const [showCopy, setShowCopy] = useState(false);

  useEffect(() => {
    if (codeRef.current) {
      Prism.highlightElement(codeRef.current);
    }
  }, [code, language, codeRef]);

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
      <pre
        className={classNames({
          [`language-${language}`]: language
        })}
      >
        <code ref={codeRef}>{code}</code>
      </pre>
    </div>
  );
};
