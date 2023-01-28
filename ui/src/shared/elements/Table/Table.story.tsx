import { useMemo } from 'react';
import { Table } from './Table';
import {
  NumberRangeColumnFilter,
  SelectColumnFilter,
  SliderColumnFilter
} from './Filters';

export default {
  title: 'Elements/Table',
  component: Table
};

const data = [
  { id: 1, name: 'Tom', age: 28 },
  { id: 2, name: 'Jerry', age: 25 },
  { id: 3, name: 'Bugs', age: 30 },
  { id: 4, name: 'Milk', age: 35 }
];

const columns = [
  {
    Header: 'ID',
    accessor: 'id'
  },
  {
    Header: 'Name',
    accessor: 'name'
  },
  {
    Header: 'Age',
    accessor: 'age'
  }
];

export const Basic = () => {
  return <Table columns={columns} data={data} />;
};

export const Striped = () => {
  return <Table columns={columns} data={data} striped />;
};

export const Compact = () => {
  return (
    <Table columns={columns} data={data} spacing="compact" border="basic" />
  );
};

export const Expanded = () => {
  return (
    <Table columns={columns} data={data} spacing="expanded" border="basic" />
  );
};

export const Filter = () => {
  const columns = useMemo(
    () => [
      {
        Header: 'Name',
        columns: [
          {
            Header: 'First Name',
            accessor: 'firstName',
            sortable: true
          },
          {
            Header: 'Last Name',
            accessor: 'lastName'
          }
        ]
      },
      {
        Header: 'Info',
        columns: [
          {
            Header: 'Age',
            accessor: 'age',
            Filter: SliderColumnFilter,
            filter: 'equals'
          },
          {
            Header: 'Visits',
            accessor: 'visits',
            Filter: NumberRangeColumnFilter,
            filter: 'between'
          },
          {
            Header: 'Status',
            accessor: 'status',
            Filter: SelectColumnFilter,
            filter: 'includes'
          }
        ]
      }
    ],
    []
  );

  const data = [
    {
      firstName: 'map',
      lastName: 'country',
      age: 15,
      visits: 22,
      status: 'relationship'
    },
    {
      firstName: 'swim',
      lastName: 'passion',
      age: 18,
      visits: 43,
      status: 'relationship'
    },
    {
      firstName: 'tramp',
      lastName: 'menu',
      age: 25,
      visits: 51,
      status: 'relationship'
    },
    {
      firstName: 'alley',
      lastName: 'battle',
      age: 22,
      visits: 12,
      status: 'relationship'
    },
    {
      firstName: 'uncle',
      lastName: 'governor',
      age: 7,
      visits: 54,
      status: 'single'
    },
    {
      firstName: 'songs',
      lastName: 'religion',
      age: 15,
      visits: 63,
      status: 'relationship'
    },
    {
      firstName: 'cork',
      lastName: 'wish',
      age: 5,
      visits: 97,
      status: 'complicated'
    },
    {
      firstName: 'kick',
      lastName: 'insurance',
      age: 13,
      visits: 91,
      status: 'single'
    },
    {
      firstName: 'meat',
      lastName: 'quiver',
      age: 2,
      visits: 94,
      status: 'complicated'
    },
    {
      firstName: 'show',
      lastName: 'sheep',
      age: 9,
      visits: 27,
      status: 'single'
    }
  ];

  return (
    <Table
      columns={columns}
      data={data}
      striped
      border="basic"
      spacing="expanded"
      selectable
    />
  );
};
