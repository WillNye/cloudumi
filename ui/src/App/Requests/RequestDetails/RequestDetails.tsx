import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'core/Axios/Axios';
import { Button } from 'shared/elements/Button';
import { Table } from 'shared/elements/Table';

import { DiffEditor } from 'shared/form/DiffEditor';
import { LineBreak } from 'shared/elements/LineBreak';
import { filePathColumns, mainTableColumns } from './constants';
import NotFound from 'App/NotFound';
import { Segment } from 'shared/layout/Segment';
import { TextArea } from 'shared/form/TextArea';
import styles from './RequestDetails.module.css';
import { Block } from 'shared/layout/Block';

const RequestChangeDetails = () => {
  const { requestId } = useParams<{ requestId: string }>();
  const [requestData, setRequestData] = useState<any>(null);
  const [comment, setComment] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const fetchRequestData = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(
        `/api/v4/self-service/requests/${requestId}`
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRequestData();
  }, [requestId]);

  const handleSave = async () => {
    setIsLoading(true);
    try {
      const response = await axios.put(
        `/api/v4/self-service/requests/${requestId}`,
        { files: requestData.files }
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleComment = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(
        `/api/v4/self-service/requests/${requestId}/comments`,
        { comment }
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async () => {
    setIsLoading(true);
    try {
      const response = await axios.patch(
        `/api/v4/self-service/requests/${requestId}`,
        { status: 'approved' }
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(
        `/api/v4/self-service/requests/${requestId}/reject`
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApply = async () => {
    setIsLoading(true);
    try {
      const response = await axios.post(
        `/api/v4/self-service/requests/${requestId}/apply`
      );
      setRequestData(response.data.data);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const mainTableData = [
    {
      header: 'Requested By',
      value: requestData?.requested_by || 'N/A'
    },
    {
      header: 'Requested At',
      value: requestData?.requested_at || 'N/A'
    },
    {
      header: 'Last Updated',
      value: requestData?.updated_at || 'N/A'
    },
    {
      header: 'Status',
      value: requestData?.status || 'N/A'
    },
    {
      header: 'Title',
      value: requestData?.title || 'N/A'
    },
    {
      header: 'Justification',
      value: requestData?.justification || 'N/A'
    },
    {
      header: 'Repository',
      value: requestData?.repo_name || 'N/A'
    },
    {
      header: 'Pull Request URL',
      value: requestData?.pull_request_url || 'N/A'
    }
  ];

  if (!requestData && !isLoading) {
    return <NotFound />;
  }

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Request Review</h3>
        <Table
          data={mainTableData}
          columns={mainTableColumns}
          spacing="expanded"
        />
        {requestData?.files.map((file, i) => (
          <div key={i}>
            <Table
              data={[{ header: 'File Path', value: file.file_path }]}
              columns={filePathColumns}
              spacing="expanded"
            />
            <DiffEditor
              original={file.previous_body || ''}
              modified={file.template_body || ''}
            />
            <LineBreak />
            <Button onClick={handleSave} fullWidth size="small">
              Modify
            </Button>
            <LineBreak />
          </div>
        ))}
        <LineBreak size="large" />
        <Block disableLabelPadding label="Comment" />
        <TextArea
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="Add a comment"
        />
        <LineBreak size="small" />
        <Button onClick={handleComment} size="small">
          Comment
        </Button>
        <LineBreak size="large" />
        <div className={styles.actions}>
          <Button onClick={handleApprove} fullWidth size="small">
            Approve
          </Button>
          <Button onClick={handleReject} color="error" fullWidth size="small">
            Reject
          </Button>
          <Button onClick={handleApply} color="success" fullWidth size="small">
            Apply
          </Button>
        </div>
      </div>
    </Segment>
  );
};

export default RequestChangeDetails;
