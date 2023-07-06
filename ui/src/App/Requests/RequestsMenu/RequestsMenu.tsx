import { Button } from 'shared/elements/Button';
import { Card } from 'shared/layout/Card';
import styles from './RequestsMenu.module.css';
import { Segment } from 'shared/layout/Segment';
import { useMemo, useState } from 'react';
import { REQUESTS_SECTIONS, myRequestsColumns } from './constants';
import { LineBreak } from 'shared/elements/LineBreak';
import { Divider } from 'shared/elements/Divider';
import { Table } from 'shared/elements/Table';
import { Icon } from 'shared/elements/Icon';
import { Link, useNavigate } from 'react-router-dom';
import awsIcon from '../../../assets/integrations/awsIcon.svg';
import oktaIcon from '../../../assets/integrations/oktaIcon.svg';
import { useQuery } from '@tanstack/react-query';
import { getAllRequests } from 'core/API/iambicRequest';
import { DateTime } from 'luxon';
import { useAuth } from 'core/Auth';

const RequestsMenu = () => {
  const [currentTab, setCurrentTab] = useState(
    REQUESTS_SECTIONS.RECENT_REQUESTS
  );

  const { user } = useAuth();

  const navigate = useNavigate();

  const query = useMemo(() => {
    return {
      pagination: {
        currentPageIndex: 1,
        pageSize: 5
      },
      sorting: {
        sortingColumn: {
          id: 'id',
          sortingField: 'repo_name',
          header: 'Repo Name',
          minWidth: 180
        },
        sortingDescending: false
      },
      filtering: {
        tokens: [
          { propertyKey: 'created_by', operator: '=', value: user?.user }
        ],
        operation: 'and'
      }
    };
  }, [user]);

  const { data: requests, isLoading } = useQuery({
    queryFn: getAllRequests,
    queryKey: ['getAllRequests', query]
  });

  const tableRows = useMemo(() => {
    return (requests?.data?.data || []).map(item => {
      return {
        repo_name: <Link to={`/requests/${item.id}`}>{item.repo_name}</Link>,
        pull_request_id: (
          <Link to={item.pull_request_url} target="_blank">
            #{item.pull_request_id}
          </Link>
        ),
        created_at: (
          <p>
            {DateTime.fromSeconds(item.created_at).toFormat(
              'yyyy/MM/dd HH:mm ZZZZ'
            )}
          </p>
        ),
        created_by: <p>{item.created_by}</p>,
        status: <p>{item.status}</p>
      };
    });
  }, [requests]);

  return (
    <div className={styles.wrapper}>
      <Segment>
        <div className={styles.header}>
          <h3>Requests</h3>

          <div className={styles.btnActions}>
            <Button
              size="small"
              onClick={() => {
                navigate('/requests/create');
              }}
            >
              <Icon name="add" /> Create Request
            </Button>
            <Divider orientation="vertical" />
            <Button
              size="small"
              color="secondary"
              onClick={() => {
                navigate('/requests/all');
              }}
            >
              View All Requests
            </Button>
          </div>
        </div>
        <LineBreak size="large" />
        <p>
          IAMbic is a multi-cloud IAM control plane that centralizes and
          simplifies access management, providing a human-readable
          representation of IAM in version control. Request access and
          streamline your cloud permissions today.
        </p>
        <LineBreak size="large" />
        <h4>Recently Accessed Providers</h4>
        <LineBreak />
        <div className={styles.providers}>
          <Card
            variant="outlined"
            color="secondary"
            className={styles.card}
            contentClassName={styles.cardContent}
          >
            <img className={styles.cardImg} src={awsIcon} />
            <LineBreak />
            <h4>AWS</h4>
            <LineBreak size="small" />
            <p>Amazon Web Services</p>
            <LineBreak size="small" />
            <Button size="small" fullWidth>
              Continue
            </Button>
          </Card>
          <Card
            variant="outlined"
            color="secondary"
            className={styles.card}
            contentClassName={styles.cardContent}
          >
            <img className={styles.cardImg} src={oktaIcon} />
            <LineBreak />
            <h4>Okta</h4>
            <LineBreak size="small" />
            <p>Okta</p>
            <LineBreak size="small" />
            <Button size="small" fullWidth>
              Continue
            </Button>
          </Card>
        </div>
        <LineBreak />
        <Divider />
        <LineBreak />
        <div>
          <nav className={styles.nav}>
            <ul className={styles.navList}>
              <li
                className={`${styles.navItem} ${
                  currentTab === REQUESTS_SECTIONS.MY_REQUESTS
                    ? styles.isActive
                    : ''
                }`}
                onClick={() => setCurrentTab(REQUESTS_SECTIONS.MY_REQUESTS)}
              >
                <div className={styles.text}>My Requests</div>
              </li>
            </ul>
          </nav>
          <LineBreak />

          <Table
            data={tableRows}
            columns={myRequestsColumns}
            border="row"
            spacing="expanded"
            isLoading={isLoading}
          />
        </div>
      </Segment>
    </div>
  );
};

export default RequestsMenu;
