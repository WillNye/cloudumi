import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'core/Axios/Axios';
import { Button } from 'shared/elements/Button';
import { Table } from 'shared/elements/Table';
import { Input } from 'shared/form/Input';

import { DiffEditor } from 'shared/form/DiffEditor';
import styles from './SelfServiceReview.module.css';
import { Spinner } from 'shared/elements/Spinner';

const SelfServiceReview = () => {
  const { requestId } = useParams<{ requestId: string }>();
  const [requestData, setRequestData] = useState<any>(null);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchRequestData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `/api/v4/self-service/requests/${requestId}`
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequestData();
  }, [requestId]);

  const handleSave = async () => {
    setLoading(true);
    try {
      const response = await axios.put(
        `/api/v4/self-service/requests/${requestId}`,
        { files: requestData.files }
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleComment = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `/api/v4/self-service/requests/${requestId}/comments`,
        { comment }
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `/api/v4/self-service/requests/${requestId}/approve`
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `/api/v4/self-service/requests/${requestId}/reject`
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `/api/v4/self-service/requests/${requestId}/apply`
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Spinner />;
  }

  if (!requestData) {
    return null;
  }

  const tableData = {
    'Requested By': requestData.requested_by || 'N/A',
    'Requested At': requestData.requested_at || 'N/A',
    'Last Updated': requestData.updated_at || 'N/A',
    Status: requestData.status || 'N/A',
    Title: requestData.title || 'N/A',
    Justification: requestData.justification || 'N/A',
    Repository: requestData.repo_name || 'N/A',
    'Pull Request URL': requestData.pull_request_url || 'N/A'
  };

  return (
    <div>
      <h2>Self Service Request Review</h2>

      {/* <Table data={tableData} /> */}

      {requestData.files.map((file, i) => (
        <div key={i}>
          <DiffEditor
            original={file.previous_body || ''}
            modified={file.template_body || ''}
          />
        </div>
      ))}

      <Button onClick={handleSave}>Save</Button>

      <Input
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Add a comment"
      />
      <Button onClick={handleComment}>Comment</Button>

      <Button onClick={handleApprove}>Approve</Button>

      <Button onClick={handleReject}>Reject</Button>

      <Button onClick={handleApply}>Apply</Button>
    </div>
  );
};

export default SelfServiceReview;
