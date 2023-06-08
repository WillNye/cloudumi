import { useContext, useMemo } from 'react';

import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';
import styles from './SelectProvider.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { Link } from 'react-router-dom';

import SelfServiceContext from '../../SelfServiceContext';
import { SELF_SERICE_STEPS } from '../../constants';
import { useQuery } from '@tanstack/react-query';
import { getProviders } from 'core/API/iambicRequest';
import { providerDetails } from './constants';

const SelectProvider = () => {
  const {
    actions: { setCurrentStep, setSelectedProvider }
  } = useContext(SelfServiceContext);

  const { data: responseData, isLoading } = useQuery({
    queryFn: getProviders,
    queryKey: ['getProviders']
  });

  const providers = useMemo(() => {
    if (responseData?.data) {
      const uniqueProviders = [
        ...new Set(responseData.data.map(item => item.provider))
      ] as string[];
      const providersData = uniqueProviders.map(provider => ({
        provider,
        ...providerDetails[provider]
      }));
      return providersData;
    }
    return [];
  }, [responseData]);

  return (
    <Segment isLoading={isLoading}>
      <div className={styles.container}>
        <h3>Select Provider</h3>
        <LineBreak />
        <p className={styles.subText}>
          Please choose a provider from the list below
        </p>
        <LineBreak size="large" />
        <div className={styles.cardList}>
          {providers.map(provider => (
            <RequestCard
              key={provider.provider}
              title={provider.title}
              icon={provider.icon}
              description={provider.description}
              onClick={() => {
                setCurrentStep(SELF_SERICE_STEPS.REQUEST_TYPE);
                setSelectedProvider(provider.provider);
              }}
            />
          ))}
        </div>
        <LineBreak size="large" />
        <p className={styles.subText}>
          Can&apos;t find what you&apos;re looking for? Have an administrator{' '}
          <Link to="/settings/integrations">click here</Link> to add a new
          provider
        </p>
      </div>
    </Segment>
  );
};

export default SelectProvider;
