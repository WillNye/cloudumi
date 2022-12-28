import React from 'react';
import Box from '@noqdev/cloudscape/box';
import Button from '@noqdev/cloudscape/button';
import CollectionPreferences from '@noqdev/cloudscape/collection-preferences';
import Pagination from '@noqdev/cloudscape/pagination';
import TextFilter from '@noqdev/cloudscape/text-filter';
import Cards from '@noqdev/cloudscape/cards';
import Header from '@noqdev/cloudscape/header';

import CloudScapeModal from '@noqdev/cloudscape/modal';
import SpaceBetween from '@noqdev/cloudscape/space-between';

export default {
  title: 'Cloudscape/Cards',
  component: Cards
};

export const CardsList = () => {
  const [selectedItems, setSelectedItems] = React.useState([
    { name: 'Item 2', description: '', type: '', size: '' }
  ]);
  return (
    <Cards
      onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
      selectedItems={selectedItems}
      ariaLabels={{
        itemSelectionLabel: (e, t) => `select ${t.name}`,
        selectionGroupLabel: 'Item selection'
      }}
      cardDefinition={{
        header: e => e.name,
        sections: [
          {
            id: 'description',
            header: 'Description',
            content: e => e.description
          },
          {
            id: 'type',
            header: 'Type',
            content: e => e.type
          },
          {
            id: 'size',
            header: 'Size',
            content: e => e.size
          }
        ]
      }}
      cardsPerRow={[{ cards: 1 }, { minWidth: 500, cards: 2 }]}
      items={[
        {
          name: 'Item 1',
          description: 'This is the first item',
          type: '1A',
          size: 'Small'
        },
        {
          name: 'Item 2',
          alt: 'Second',
          description: 'This is the second item',
          type: '1B',
          size: 'Large'
        },
        {
          name: 'Item 3',
          alt: 'Third',
          description: 'This is the third item',
          type: '1A',
          size: 'Large'
        },
        {
          name: 'Item 4',
          alt: 'Fourth',
          description: 'This is the fourth item',
          type: '2A',
          size: 'Small'
        },
        {
          name: 'Item 5',
          alt: 'Fifth',
          description: 'This is the fifth item',
          type: '2A',
          size: 'Large'
        },
        {
          name: 'Item 6',
          alt: 'Sixth',
          description: 'This is the sixth item',
          type: '1A',
          size: 'Small'
        }
      ]}
      loadingText="Loading resources"
      selectionType="multi"
      trackBy="name"
      visibleSections={['description', 'type', 'size']}
      empty={
        <Box textAlign="center" color="inherit">
          <b>No resources</b>
          <Box padding={{ bottom: 's' }} variant="p" color="inherit">
            No resources to display.
          </Box>
          <Button>Create resource</Button>
        </Box>
      }
      filter={
        <TextFilter filteringText="" filteringPlaceholder="Find resources" />
      }
      header={
        <Header
          counter={
            selectedItems.length ? '(' + selectedItems.length + '/10)' : '(10)'
          }
        >
          Common cards with selection
        </Header>
      }
      pagination={<Pagination currentPageIndex={1} pagesCount={2} />}
      preferences={
        <CollectionPreferences
          title="Preferences"
          confirmLabel="Confirm"
          cancelLabel="Cancel"
          preferences={{
            pageSize: 6,
            visibleContent: ['description', 'type', 'size']
          }}
          pageSizePreference={{
            title: 'Select page size',
            options: [
              { value: 6, label: '6 resources' },
              { value: 12, label: '12 resources' }
            ]
          }}
          visibleContentPreference={{
            title: 'Select visible content',
            options: [
              {
                label: 'Main distribution properties',
                options: [
                  {
                    id: 'description',
                    label: 'Description'
                  },
                  { id: 'type', label: 'Type' },
                  { id: 'size', label: 'Size' }
                ]
              }
            ]
          }}
        />
      }
    />
  );
};

export const Modal = () => {
  const [visible, setVisible] = React.useState(false);
  return (
    <>
      <Button variant="normal" onClick={() => setVisible(true)}>
        Open Modal
      </Button>
      <CloudScapeModal
        onDismiss={() => setVisible(false)}
        visible={visible}
        closeAriaLabel="Close modal"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link">Cancel</Button>
              <Button variant="primary">Ok</Button>
            </SpaceBetween>
          </Box>
        }
        header="Modal title"
      >
        Your description should go here
      </CloudScapeModal>
    </>
  );
};
