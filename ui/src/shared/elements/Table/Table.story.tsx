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
    header: 'ID',
    accessorKey: 'id'
  },
  {
    header: 'Name',
    accessorKey: 'name'
  },
  {
    header: 'Age',
    accessorKey: 'age'
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
        header: 'Name',
        columns: [
          {
            header: 'First Name',
            accessorKey: 'firstName'
          },
          {
            header: 'Last Name',
            accessorKey: 'lastName'
          }
        ]
      },
      {
        header: 'Info',
        columns: [
          {
            header: 'Age',
            accessorKey: 'age',
            Filter: SliderColumnFilter,
            filter: 'equals'
          },
          {
            header: 'Visits',
            accessorKey: 'visits',
            Filter: NumberRangeColumnFilter,
            filter: 'between'
          },
          {
            header: 'Status',
            accessorKey: 'status',
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
      enableRowSelection
    />
  );
};
