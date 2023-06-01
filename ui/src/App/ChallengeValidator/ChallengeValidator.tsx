import { useEffect, useState } from 'react';
import styles from './ChallengeValidator.module.css';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Button } from 'shared/elements/Button';
import { Segment } from 'shared/layout/Segment';
import { LineBreak } from 'shared/elements/LineBreak';

interface ChallengeValidatorResponse {
  message: string;
  nonce?: string;
  show_approve_button?: boolean;
}

const ChallengeValidator = () => {
  const { challengeToken } = useParams<{ challengeToken: string }>();
  const [result, setResult] = useState<ChallengeValidatorResponse | null>(null);
  const [showApproveButton, setShowApproveButton] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const response = await axios.get<ChallengeValidatorResponse>(
          '/api/v2/challenge_validator/' + challengeToken
        );
        setResult(response.data);
        setShowApproveButton(response.data.show_approve_button || false);
      } catch (err) {
        console.error(err);
      }
    })();
  }, [challengeToken]);

  const validateChallengeToken = async () => {
    if (!result?.nonce) {
      return;
    }

    try {
      const response = await axios.post<ChallengeValidatorResponse>(
        '/api/v2/challenge_validator/' + challengeToken,
        { nonce: result.nonce }
      );
      setResult(response.data);
      setShowApproveButton(false);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className={styles.container}>
      <Segment>
        <div className={styles.markdownContainer}>
          <ReactMarkdown linkTarget="_blank">{result?.message}</ReactMarkdown>
        </div>
        <LineBreak />
        {showApproveButton ? (
          <Button color="primary" size="small" onClick={validateChallengeToken}>
            Approve Credential Request
          </Button>
        ) : null}
      </Segment>
    </div>
  );
};

export default ChallengeValidator;
