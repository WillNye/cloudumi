import { useState } from 'react';
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
import { useQuery } from '@tanstack/react-query';
import { getIambicRequest } from 'core/API/iambicRequest';
import { Loader } from 'shared/elements/Loader';

const RequestChangeDetails = () => {
  const { requestId } = useParams<{ requestId: string }>();
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    refetch: refetchData,
    data: requestData,
    isLoading
  } = useQuery({
    queryFn: getIambicRequest,
    queryKey: ['getIambicRequest', requestId]
  });

  const handleSave = async () => {
    setIsSubmitting(true);
    try {
      await axios.put(`/api/v4/self-service/requests/${requestId}`, {
        files: requestData.files
      });
      refetchData();
    } catch (error) {
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleComment = async () => {
    setIsSubmitting(true);
    try {
      await axios.post(`/api/v4/self-service/requests/${requestId}/comments`, {
        comment
      });
      refetchData();
    } catch (error) {
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await axios.patch(`/api/v4/self-service/requests/${requestId}`, {
        status: 'approved'
      });
      refetchData();
    } catch (error) {
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    try {
      await axios.post(`/api/v4/self-service/requests/${requestId}/reject`);
      refetchData();
    } catch (error) {
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApply = async () => {
    setIsSubmitting(true);
    try {
      await axios.post(`/api/v4/self-service/requests/${requestId}/apply`);
      refetchData();
    } catch (error) {
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const mainTableData = [
    {
      header: 'Requested By',
      value: requestData?.data?.requested_by || 'N/A'
    },
    {
      header: 'Requested At',
      value: requestData?.data?.requested_at || 'N/A'
    },
    {
      header: 'Last Updated',
      value: requestData?.data?.updated_at || 'N/A'
    },
    {
      header: 'Status',
      value: requestData?.data?.status || 'N/A'
    },
    {
      header: 'Title',
      value: requestData?.data?.title || 'N/A'
    },
    {
      header: 'Justification',
      value: requestData?.data?.justification || 'N/A'
    },
    {
      header: 'Repository',
      value: requestData?.data?.repo_name || 'N/A'
    },
    {
      header: 'Pull Request URL',
      value: requestData?.data?.pull_request_url || 'N/A'
    }
  ];

  if (isLoading) {
    return <Loader />;
  }

  if (!requestData?.data) {
    return <NotFound />;
  }

  return (
    <Segment isLoading={isSubmitting}>
      <div className={styles.container}>
        <h3>Request Review</h3>
        <Table
          data={mainTableData}
          columns={mainTableColumns}
          spacing="expanded"
          border="row"
        />
        {requestData?.data?.files.map((file, i) => (
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
