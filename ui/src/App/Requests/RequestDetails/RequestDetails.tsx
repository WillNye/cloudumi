import { useCallback, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import axios from 'core/Axios/Axios';
import { Button } from 'shared/elements/Button';
import { Table } from 'shared/elements/Table';

import { LineBreak } from 'shared/elements/LineBreak';
import { mainTableColumns } from './constants';
import NotFound from 'App/NotFound';
import { Segment } from 'shared/layout/Segment';
import { TextArea } from 'shared/form/TextArea';
import styles from './RequestDetails.module.css';
import { Block } from 'shared/layout/Block';
import { useQuery } from '@tanstack/react-query';
import { getIambicRequest } from 'core/API/iambicRequest';
import { Loader } from 'shared/elements/Loader';
import { Chip, ChipType } from 'shared/elements/Chip';
import ChangeViewer from './components/ChangeViewer';

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

  const handleComment = useCallback(async () => {
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
      setComment('');
    }
  }, [comment, requestId, refetchData]);

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
      await axios.patch(`/api/v4/self-service/requests/${requestId}`, {
        status: 'rejected'
      });
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

  const handleModifyChange = useCallback(
    async newFile => {
      setIsSubmitting(true);
      try {
        await axios.put(`/api/v4/self-service/requests/${requestId}`, {
          files: requestData?.data.files?.map(currentFile => {
            if (newFile.file_path === currentFile.file_path) {
              return newFile;
            }
            return currentFile;
          })
        });
        refetchData();
        setIsSubmitting(false);
      } catch (error) {
        console.error(error);
        setIsSubmitting(false);
      }
    },
    [refetchData, requestData, requestId]
  );

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
      header: 'Repository',
      value: requestData?.data?.repo_name || 'N/A'
    },
    {
      header: 'Pull Request URL',
      value: requestData?.data?.pull_request_url ? (
        <Link to={requestData?.data?.pull_request_url} target="_blank">
          Click here
        </Link>
      ) : (
        'N/A'
      )
    },
    {
      header: 'Justification',
      value: requestData?.data?.justification
    }
  ];

  const getRequestStatus = useCallback(status => {
    switch (status) {
      case 'Approved':
      case 'Running':
        return 'success' as ChipType;
      case 'Pending':
      case 'Pending in Git':
        return 'warning' as ChipType;
      case 'Rejected':
      case 'Failed':
        return 'danger' as ChipType;
      case 'Expired':
        return 'warning' as ChipType;
      default:
        return 'dark' as ChipType;
    }
  }, []);

  const chipClass = useMemo(
    (): ChipType => getRequestStatus(requestData?.data?.status),
    [getRequestStatus, requestData?.data?.status]
  );

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
        <div className={styles.subTitle}>
          <p className={styles.text}>{requestData?.data?.title}</p>
          <Chip type={chipClass}>{requestData?.data?.status}</Chip>
        </div>
        <Table data={mainTableData} columns={mainTableColumns} border="row" />
        <LineBreak size="large" />

        {requestData?.data?.files.map((file, index) => (
          <ChangeViewer
            file={file}
            handleModifyChange={handleModifyChange}
            key={index}
          />
        ))}
        <LineBreak size="large" />
        {requestData?.data?.comments.map((commentData, index) => (
          <div key={index}>{commentData?.body}</div>
        ))}
        <Block disableLabelPadding label="Comment" />
        <TextArea
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="Add a comment"
        />
        <LineBreak size="small" />
        <Button onClick={handleComment} size="small" disabled={!comment}>
          Comment
        </Button>
        <LineBreak size="large" />
        <div className={styles.actions}>
          <Button onClick={handleReject} color="error" fullWidth size="small">
            Reject
          </Button>
          <Button onClick={handleApprove} fullWidth size="small">
            Approve
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
