import { useEffect, useState } from 'react';
import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';

import styles from './SelectRequestType.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { useContext } from 'react';
import SelfServiceContext from '../../SelfServiceContext';
import { SELF_SERVICE_STEPS } from '../../constants';
import { RequestType } from '../../types';
import { useQuery } from '@tanstack/react-query';
import { getRequestType } from 'core/API/iambicRequest';
import { AxiosError } from 'axios';
import { getRequestTypeIcon } from './utils';
import NoResults from '../NoResults/NoResults';

const SelectRequestType = () => {
  const { selfServiceRequest } = useContext(SelfServiceContext).store;

  const {
    actions: { setCurrentStep, setSelectedRequestType, setRequestTypes }
  } = useContext(SelfServiceContext);

  const { data, isLoading } = useQuery({
    queryFn: getRequestType,
    queryKey: [
      'getRequestType',
      selfServiceRequest.provider,
      selfServiceRequest.identityType
    ],
    onError: (error: AxiosError) => {
      // const errorRes = error?.response;
      // const errorMsg = extractErrorMessage(errorRes?.data);
      // setErrorMessage(errorMsg || 'An error occurred fetching resource');
    }
  });

  useEffect(() => {
    if (data?.data?.length) {
      setRequestTypes(data.data);
    }
  }, [data, setRequestTypes]);

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Request Type</h3>
        <LineBreak />
        <p className={styles.subText}>What would you like to do?</p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          {selfServiceRequest?.requestTypes?.length ? (
            selfServiceRequest?.requestTypes.map(requestType => (
              <RequestCard
                key={requestType.id}
                title={requestType.name}
                icon={getRequestTypeIcon(requestType.name)}
                description={requestType.description}
                onClick={() => {
                  setCurrentStep(SELF_SERVICE_STEPS.CHANGE_TYPE);
                  setSelectedRequestType(requestType);
                }}
              />
            ))
          ) : (
            <NoResults />
          )}
        </div>
      </div>
    </Segment>
  );
};

export default SelectRequestType;

// import { useEffect, useMemo, useState } from 'react';
// import { Segment } from 'shared/layout/Segment';
// import RequestCard from '../RequestCard';

// import styles from './SelectRequestType.module.css';
// import { LineBreak } from 'shared/elements/LineBreak';
// import { useContext } from 'react';
// import SelfServiceContext from '../../SelfServiceContext';
// import { SELF_SERVICE_STEPS } from '../../constants';
// import { RequestType, ChangeType } from '../../types';
// import { useQuery } from '@tanstack/react-query';
// import { getRequestType, getChangeRequestType,
//   getProviderDefinitions } from 'core/API/iambicRequest';
// import { AxiosError } from 'axios';
// import { getRequestTypeIcon } from './utils';
// import NoResults from '../NoResults/NoResults';
// import { Button } from 'shared/elements/Button';
// import { Select as CloudScapeSelect } from '@noqdev/cloudscape';
// import { Block } from 'shared/layout/Block';
// import RequestChangeDetails from '../RequestChangeDetails';
// import { Table } from 'shared/elements/Table';

// const SelectRequestType = () => {
//   const { selfServiceRequest } = useContext(SelfServiceContext).store;

//   const {
//     actions: { setCurrentStep, setSelectedRequestType, setRequestTypes, addChange, removeChange } // Add setSelectedChangeType and addChange actions
//   } = useContext(SelfServiceContext);

//   const { data, isLoading } = useQuery({
//     queryFn: getRequestType,
//     queryKey: [
//       'getRequestType',
//       selfServiceRequest.provider,
//       selfServiceRequest.identityType
//     ],
//     onError: (error: AxiosError) => {
//       // const errorRes = error?.response;
//       // const errorMsg = extractErrorMessage(errorRes?.data);
//       // setErrorMessage(errorMsg || 'An error occurred fetching resource');
//     }
//   });

//   const { data: providerDefinition, isLoading: loadingDefinitions } = useQuery({
//     queryFn: getProviderDefinitions,
//     queryKey: [
//       'getProviderDefinitions',
//       {
//         provider: selfServiceRequest?.provider,
//         template_id: selfServiceRequest?.identity
//           ? selfServiceRequest.identity?.id
//           : null
//       }
//     ],
//     onError: (error: AxiosError) => {
//       // const errorRes = error?.response;
//       // const errorMsg = extractErrorMessage(errorRes?.data);
//       // setErrorMessage(errorMsg || 'An error occurred fetching resource');
//     }
//   });

//   useEffect(() => {
//     setSelectedChangeType(null);
//     // code to reset change-type settings goes here
//   }, [selfServiceRequest?.requestType]);

//   // New state for selected change type
//   const [selectedChangeType, setSelectedChangeType] = useState<ChangeType | null>(null);

//   // New query for change types
//   const { data: changeTypes, isLoading: isLoadingChangeTypes } = useQuery({
//     queryFn: getChangeRequestType,
//     queryKey: ['getChangeRequestType', selfServiceRequest.requestType?.id],
//     onError: (error: AxiosError) => {
//       // const errorRes = error?.response;
//       // const errorMsg = extractErrorMessage(errorRes?.data);
//       // setErrorMessage(errorMsg || 'An error occurred fetching resource');
//     }
//   });

//   // New handler for change type selection
//   const handleSelectChange = (detail: any) => {
//     const selectedChange = changeTypes?.data.find(
//       changeType => changeType.id === detail.value
//     );
//     setSelectedChangeType(selectedChange);
//     // Do something with the selected option
//   };

//   const tableRows = useMemo(
//     () => selfServiceRequest.requestedChanges,
//     [selfServiceRequest]
//   );

//   const changesColumns = useMemo(
//     () => [
//       {
//         header: 'Change Name',
//         accessorKey: 'name',
//         sortable: false
//       },
//       {
//         header: 'Description',
//         accessorKey: 'description',
//         sortable: true
//       },
//       // {
//       //   header: 'Field Changes',
//       //   accessorKey: 'fields',
//       //   sortable: false,
//       //   Cell: ({ value }) => (
//       //     <ul>
//       //       {value.map(field => (
//       //         <li key={field.field_key}>
//       //           {field.field_key}: {field.value}
//       //         </li>
//       //       ))}
//       //     </ul>
//       //   )
//       // },
//       {
//         header: 'Actions',
//         accessorKey: 'id',
//         sortable: false,
//         Cell: ({ row: { index } }) => {
//           return (
//             <Button
//               onClick={() => removeChange(index)}
//               color="secondary"
//               size="small"
//             >
//               Remove
//             </Button>
//           );
//         }
//       }
//     ],
//     [removeChange]
//   );

//   useEffect(() => {
//     if (data?.data?.length && JSON.stringify(data.data) !== JSON.stringify(selfServiceRequest.requestTypes)) {
//       setRequestTypes(data.data);
//     }
//   }, [data, selfServiceRequest.requestTypes]);

//   return (
//     <Segment isLoading={isLoading}>
//       <div className={styles.container}>
//       <h3>Request Type</h3>
//       <LineBreak />
//       <p className={styles.subText}>What would you like to do?</p>
//       <LineBreak size="large" />
//       <div className={styles.navcontainer}>
//       <nav className={styles.nav}>
//       <ul className={styles.navList}>
//         {data?.data?.map((requestType) => (
//           <li
//             key={requestType.id}
//             className={`${styles.navItem} ${selfServiceRequest?.requestType?.id === requestType.id ? styles.isActive : ''}`}
//             onClick={() => {
//               setSelectedRequestType(requestType);
//             }}
//           >
//             {requestType.name}
//           </li>
//         ))}
//       </ul>
//     </nav>
//     </div>
//       <LineBreak size="large" />

//           {/* New code for selecting and adding a change */}
//           {selfServiceRequest.requestType && (
//             <>
//               <h3>Select Change Type</h3>
//               <LineBreak />
//               <p className={styles.subText}>Please select a change type</p>
//               <LineBreak size="large" />
//               <div className={styles.content}>
//                 <Block disableLabelPadding label="Change Type" />
//                 <CloudScapeSelect
//                   selectedOption={
//                     selectedChangeType && {
//                       label: selectedChangeType.name,
//                       value: selectedChangeType.id,
//                       description: selectedChangeType.description
//                     }
//                   }
//                   onChange={({ detail }) => handleSelectChange(detail.selectedOption)}
//                   options={changeTypes?.data?.map(changeType => ({
//                     label: changeType.name,
//                     value: changeType.id,
//                     description: changeType.description
//                   }))}
//                   filteringType="auto"
//                   selectedAriaLabel="Selected"
//                   placeholder="Select change type"
//                 />
//                 <LineBreak size="large" />
//           {selectedChangeType && (
//             <RequestChangeDetails
//               selectedChangeType={selectedChangeType}
//               providerDefinition={providerDefinition?.data || []}
//             />
//           )}
//           <LineBreak size="large" />
//           <h4>Selected Changes</h4>
//           <LineBreak size="small" />
//           <Table
//             data={tableRows}
//             columns={changesColumns}
//             noResultsComponent={
//               <div className={styles.subText}>
//                 Please add changes to the request
//               </div>
//             }
//             border="row"
//           />
//               </div>
//             </>
//           )}
//         </div>
//       </Segment>
//     );
//   };

//   export default SelectRequestType;
