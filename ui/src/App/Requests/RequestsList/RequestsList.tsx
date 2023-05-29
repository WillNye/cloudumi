import { LineBreak } from 'shared/elements/LineBreak';
import { Table } from 'shared/elements/Table';
import { Segment } from 'shared/layout/Segment';
import { requestsColumns } from './constants';
import { Button } from 'shared/elements/Button';
import { Divider } from 'shared/elements/Divider';
import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useRef, useState } from 'react';
import styles from './RequestsList.module.css';
import { Icon } from 'shared/elements/Icon';
import { Select, SelectOption } from 'shared/form/Select';
import { Menu } from 'shared/layers/Menu';
import { Checkbox } from 'shared/form/Checkbox';
import { useNavigate } from 'react-router-dom';

const RequestsList = () => {
  const statusRef = useRef();
  const columnsRef = useRef();

  const navigate = useNavigate();

  const [isStatusMenuOpen, setIsStatusMenuOpen] = useState(false);
  const [isColumnMenuOpen, setIsColumnMenuOpen] = useState(false);
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
            countText="5 matches"
            filteringOptions={[]}
            filteringProperties={[
              {
                key: 'account_name',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Account Name',
                groupValuesLabel: 'Account Name values'
              },
              {
                key: 'account_id',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Account ID',
                groupValuesLabel: 'Account ID values'
              },
              {
                key: 'role_name',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Role Name',
                groupValuesLabel: 'Role Name values'
              }
            ]}
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

              <Button
                size="small"
                color="secondary"
                variant="text"
                ref={columnsRef}
                onClick={() => setIsColumnMenuOpen(statusValue => !statusValue)}
              >
                Columns <Icon name="chevron-down" size="large" />
              </Button>
              <Menu
                open={isColumnMenuOpen}
                onClose={() => setIsColumnMenuOpen(false)}
                reference={columnsRef}
              >
                <div>
                  <Checkbox defaultChecked /> User
                </div>
                <div>
                  <Checkbox defaultChecked /> Request ID
                </div>
                <div>
                  <Checkbox defaultChecked /> ARN
                </div>
                <div>
                  <Checkbox defaultChecked /> Status
                </div>
                <div>
                  <Checkbox defaultChecked /> Created At
                </div>
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
        <Table data={[]} columns={requestsColumns} border="row" />
      </div>
    </Segment>
  );
};

export default RequestsList;
