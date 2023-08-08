import { Button } from 'shared/elements/Button';
import styles from './RequestsMenu.module.css';
import { Segment } from 'shared/layout/Segment';
import { useMemo, useState } from 'react';
import { REQUESTS_SECTIONS, myRequestsColumns } from './constants';
import { LineBreak } from 'shared/elements/LineBreak';
import { Table } from 'shared/elements/Table';
import { Icon } from 'shared/elements/Icon';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAllRequests } from 'core/API/iambicRequest';
import { DateTime } from 'luxon';
import { useAuth } from 'core/Auth';
import { Breadcrumbs } from 'shared/elements/Breadcrumbs';

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
        <h3>Requests</h3>
        <LineBreak />
        <Breadcrumbs
          items={[
            { name: 'Requests', url: '/requests' },
            { name: 'Menu', url: '/requests' }
          ]}
        />
        <LineBreak />
        <div className={styles.preview}>
          <LineBreak />
          <div className={styles.btnActions}>
            <Button
              size="small"
              onClick={() => {
                navigate('/requests/create');
              }}
            >
              <Icon name="add" /> Create Self-Service Request
            </Button>
            <Button
              size="small"
              color="secondary"
              variant="outline"
              onClick={() => {
                navigate('/requests/all');
              }}
            >
              View All Requests
            </Button>
          </div>
        </div>
        <LineBreak size="large" />
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
