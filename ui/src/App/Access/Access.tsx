import { FC, useMemo, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';

import css from './Access.module.css';
import { Table } from 'shared/elements/Table';
import { Button } from 'shared/elements/Button';
import { Link } from 'react-router-dom';
import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { Icon } from 'shared/elements/Icon';
import { Menu } from 'shared/layers/Menu';
import { Dialog } from 'shared/layers/Dialog';

export interface AccessRole {
  arn: string;
  account_name: string;
  account_id: string;
  role_name: string;
  redirect_uri: string;
  inactive_tra: boolean;
}

export interface AccessQueryResult {
  totalCount: number;
  filteredCount: number;
  data: AccessRole[];
}

type AccessProps = AccessQueryResult;

const columns = [
  {
    accessor: 'arn',
    width: '220px'
  },
  {
    Header: 'Name',
    accessor: 'name',
    sortable: true
  },
  {
    Header: 'Role',
    accessor: 'roleName',
    sortable: true
  },
  {
    accessor: 'viewDetails',
    width: '50px'
  },
  {
    accessor: 'moreActions',
    width: '50px'
  }
];

const MoreActions = () => {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);

  return (
    <>
      <div ref={buttonRef} onClick={() => setOpen(!open)}>
        <Icon name="more" size="large" color="secondary" />
      </div>
      <Menu open={open} onClose={() => setOpen(false)} reference={buttonRef}>
        <div>
          <Button variant="text" color="secondary" size="small" fullWidth>
            Add Permissions
          </Button>
          <Button variant="text" color="secondary" size="small" fullWidth>
            View Details
          </Button>
        </div>
      </Menu>
    </>
  );
};

const RoleCredentailSummary = () => {
  const [showDialog, setShowDialog] = useState(false);

  return (
    <>
      <div onClick={() => setShowDialog(!showDialog)}>
        <Icon name="break-glass" size="large" color="secondary" />
      </div>
      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        size="medium"
      >
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
        <br />
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
        <br />
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
        <br />
        <pre>
          Noq CLI To retrieve AWS credentials on demand noq credential_process
          -g prod/prod_admin noq serve prod/prod_admin noq file prod/prod_admin
          -p prod/prod_admin noq export prod/prod_admin
        </pre>
      </Dialog>
    </>
  );
};

export const Access: FC<AccessProps> = ({ data }) => {
  const [query, setQuery] = useState<PropertyFilterProps.Query>({
    tokens: [],
    operation: 'and'
  });

  const tableRowss = useMemo(() => {
    return data.map(item => {
      return {
        ...item,
        roleName: (
          <Link to={`/resources/edit/${item.arn}`}>
            {item.role_name.match(/\[(.+?)\]\((.+?)\)/)[1]}
          </Link>
        ),
        name: (
          <div>
            <div>{item.account_name}</div>
            <div className={css.tableSecondaryText}>{item.account_id}</div>
          </div>
        ),
        arn: (
          <Button
            fullWidth
            color={item.inactive_tra ? 'secondary' : 'primary'}
            size="small"
          >
            {item.inactive_tra ? 'Request Temporary Access' : 'Signin'}
          </Button>
        ),
        viewDetails: <RoleCredentailSummary />,
        moreActions: <MoreActions />
      };
    });
  }, [data]);

  return (
    <>
      <Helmet>
        <title>Access</title>
      </Helmet>
      <div className={css.container}>
        <div className={css.filter}>
          <PropertyFilter
            expandToViewport
            onChange={({ detail }) => setQuery(detail)}
            query={query}
            i18nStrings={{
              filteringAriaLabel: 'your choice',
              dismissAriaLabel: 'Dismiss',
              filteringPlaceholder:
                'Filter distributions by text, property or value',
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
            filteringOptions={[
              {
                propertyKey: 'instanceid',
                value: 'i-2dc5ce28a0328391'
              },
              {
                propertyKey: 'instanceid',
                value: 'i-d0312e022392efa0'
              },
              {
                propertyKey: 'instanceid',
                value: 'i-070eef935c1301e6'
              },
              {
                propertyKey: 'instanceid',
                value: 'i-3b44795b1fea36ac'
              },
              { propertyKey: 'state', value: 'Stopped' },
              { propertyKey: 'state', value: 'Stopping' },
              { propertyKey: 'state', value: 'Pending' },
              { propertyKey: 'state', value: 'Running' },
              {
                propertyKey: 'instancetype',
                value: 't3.small'
              },
              {
                propertyKey: 'instancetype',
                value: 't2.small'
              },
              { propertyKey: 'instancetype', value: 't3.nano' },
              {
                propertyKey: 'instancetype',
                value: 't2.medium'
              },
              {
                propertyKey: 'instancetype',
                value: 't3.medium'
              },
              {
                propertyKey: 'instancetype',
                value: 't2.large'
              },
              { propertyKey: 'instancetype', value: 't2.nano' },
              {
                propertyKey: 'instancetype',
                value: 't2.micro'
              },
              {
                propertyKey: 'instancetype',
                value: 't3.large'
              },
              {
                propertyKey: 'instancetype',
                value: 't3.micro'
              },
              { propertyKey: 'averagelatency', value: '17' },
              { propertyKey: 'averagelatency', value: '53' },
              { propertyKey: 'averagelatency', value: '73' },
              { propertyKey: 'averagelatency', value: '74' },
              { propertyKey: 'averagelatency', value: '107' },
              { propertyKey: 'averagelatency', value: '236' },
              { propertyKey: 'averagelatency', value: '242' },
              { propertyKey: 'averagelatency', value: '375' },
              { propertyKey: 'averagelatency', value: '402' },
              { propertyKey: 'averagelatency', value: '636' },
              { propertyKey: 'averagelatency', value: '639' },
              { propertyKey: 'averagelatency', value: '743' },
              { propertyKey: 'averagelatency', value: '835' },
              { propertyKey: 'averagelatency', value: '981' },
              { propertyKey: 'averagelatency', value: '995' }
            ]}
            filteringProperties={[
              {
                key: 'instanceid',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Instance ID',
                groupValuesLabel: 'Instance ID values'
              },
              {
                key: 'state',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'State',
                groupValuesLabel: 'State values'
              },
              {
                key: 'instancetype',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Instance type',
                groupValuesLabel: 'Instance type values'
              },
              {
                key: 'averagelatency',
                operators: ['=', '!=', '>', '<', '<=', '>='],
                propertyLabel: 'Average latency',
                groupValuesLabel: 'Average latency values'
              }
            ]}
          />
        </div>
        <Table data={tableRowss} columns={columns} border="row" />
      </div>
    </>
  );
};
