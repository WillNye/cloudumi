import { useState, useEffect, useContext } from 'react';
import axios from 'core/Axios/Axios';

import { Segment } from 'shared/layout/Segment';
import RequestCard from '../RequestCard';
import awsIcon from 'assets/integrations/awsIcon.svg';
import gsuiteIcon from 'assets/integrations/gsuiteIcon.svg';
import azureADIcon from 'assets/integrations/azureADIcon.svg';
import oktaIcon from 'assets/integrations/oktaIcon.svg';
import styles from './SelectProvider.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { Link } from 'react-router-dom';

import SelfServiceContext from '../../SelfServiceContext';
import { SELF_SERICE_STEPS } from '../../constants';

interface ProviderData {
  provider: string;
  sub_type: string;
}

interface ApiResponse {
  status_code: number;
  data: ProviderData[];
}

interface ProviderDetails {
  title: string;
  icon: string;
  description: string;
}

interface Provider {
  provider: string;
  title: string;
  icon: string;
  description: string;
}

const SelectProvider = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const {
    actions: { setCurrentStep, setSelectedProvider }
  } = useContext(SelfServiceContext);

  useEffect(() => {
    const fetchData = async () => {
      const result = await axios.get<ApiResponse>('/api/v4/providers');

      const uniqueProviders = [
        ...new Set(result.data.data.map(item => item.provider))
      ];

      const providersData: Provider[] = uniqueProviders.map(provider => ({
        provider,
        ...providerDetails[provider]
      }));

      setProviders(providersData);
    };

    fetchData();
  }, []);

  const providerDetails: Record<string, ProviderDetails> = {
    aws: {
      title: 'AWS',
      icon: awsIcon,
      description: 'Amazon web services (AWS)'
    },
    okta: { title: 'Okta', icon: oktaIcon, description: 'Okta' },
    azure_ad: {
      title: 'Azure AD',
      icon: azureADIcon,
      description: 'Azure Active Directory'
    },
    google_workspace: {
      title: 'Google Workspace',
      icon: gsuiteIcon,
      description: 'Google Workspace'
    }
  };

  return (
    <Segment>
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
