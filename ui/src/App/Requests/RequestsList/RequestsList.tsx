import { LineBreak } from 'shared/elements/LineBreak';
import { Table } from 'shared/elements/Table';
import { Segment } from 'shared/layout/Segment';
import { requestsColumns } from './constants';
import { Button } from 'shared/elements/Button';
import { Divider } from 'shared/elements/Divider';
import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useEffect, useMemo, useRef, useState } from 'react';
import styles from './RequestsList.module.css';
import { Icon } from 'shared/elements/Icon';
import { Menu } from 'shared/layers/Menu';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import axios from 'core/Axios/Axios';
import { DateTime } from 'luxon';

const RequestsList = () => {
  const [data, setData] = useState([]);
  const statusRef = useRef();

  const navigate = useNavigate();

  const [isStatusMenuOpen, setIsStatusMenuOpen] = useState(false);
  const [filter, setFilter] = useState<PropertyFilterProps.Query>({
    tokens: [],
    operation: 'and'
  });

  const [query, setQuery] = useState({
    pagination: {
      currentPageIndex: 1,
      pageSize: 30
    },
    sorting: {
      sortingColumn: {
        id: 'id',
        sortingField: 'account_name',
        header: 'Account Name',
        minWidth: 180
      },
      sortingDescending: false
    },
    filtering: filter
  });

  useEffect(() => {
    axios.get('/api/v4/self-service/requests/').then(response => {
      setData(response.data.data);
    });
  }, [query]);

  const tableRows = useMemo(() => {
    return (data || []).map(item => {
      return {
        repo_name: <p>{item.repo_name}</p>,
        pull_request_id: (
          <a href={item.pull_request_url}>#{item.pull_request_id}</a>
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
  }, [data]);

  return (
    <Segment>
      <div className={styles.wrapper}>
        <h3>All Requests</h3>
        <LineBreak />
        <div>
          <PropertyFilter
            expandToViewport
            onChange={({ detail }) => setFilter(detail)}
            query={filter}
            i18nStrings={{
              filteringAriaLabel: 'your choice',
              dismissAriaLabel: 'Dismiss',
              // filteringPlaceholder: ROLE_PROPERTY_SEARCH_FILTER,
              groupValuesText: 'Values',
              groupPropertiesText: 'Properties',
              operatorsText: 'Operators',
              operationAndText: 'and',
              operationOrText: 'or',
              operatorLessText: 'Less than',
              operatorLessOrEqualText: 'Less than or equal',
              operatorGreaterText: 'Greater than',
              operatorGreaterOrEqualText: 'Greater than or equal',
              operatorContainsText: 'Contains',
              operatorDoesNotContainText: 'Does not contain',
              operatorEqualsText: 'Equals',
              operatorDoesNotEqualText: 'Does not equal',
              editTokenHeader: 'Edit filter',
              propertyText: 'Property',
              operatorText: 'Operator',
              valueText: 'Value',
              cancelActionText: 'Cancel',
              applyActionText: 'Apply',
              allPropertiesLabel: 'All properties',
              tokenLimitShowMore: 'Show more',
              tokenLimitShowFewer: 'Show fewer',
              clearFiltersText: 'Clear filters',
              removeTokenButtonAriaLabel: token =>
                `Remove token ${token.propertyKey} ${token.operator} ${token.value}`,
              enteredTextLabel: text => `Use: "${text}"`
            }}
            filteringOptions={[]}
            filteringProperties={requestsColumns.map(column => ({
              key: column.id,
              operators: ['=', '!=', ':', '!:'],
              propertyLabel: column.header,
              groupValuesLabel: column.header + ' values'
            }))}
          />
          <LineBreak size="large" />
          <div className={styles.actionsBar}>
            <div>
              <Button
                size="small"
                color="secondary"
                variant="text"
                ref={statusRef}
                onClick={() => setIsStatusMenuOpen(statusValue => !statusValue)}
              >
                Status <Icon name="chevron-down" size="large" />
              </Button>
              <Menu
                open={isStatusMenuOpen}
                onClose={() => setIsStatusMenuOpen(false)}
                reference={statusRef}
              >
                <div>Approved</div>
                <div>Expired</div>
                <div>Pending</div>
                <div>Closed</div>
              </Menu>
            </div>
            <div className={styles.exportActions}>
              <Button
                size="small"
                onClick={() => navigate('/requests/create/')}
              >
                <Icon name="add" /> Create Request
              </Button>
              <Divider orientation="vertical"></Divider>
              <Button size="small" color="secondary">
                Export JSON
              </Button>
              <Divider orientation="vertical"></Divider>
              <Button size="small" color="secondary">
                Export CSV
              </Button>
            </div>
          </div>
        </div>
        <LineBreak size="large" />
        <Table
          data={tableRows}
          columns={requestsColumns}
          border="row"
          enableColumnVisibility
        />
      </div>
    </Segment>
  );
};

export default RequestsList;
