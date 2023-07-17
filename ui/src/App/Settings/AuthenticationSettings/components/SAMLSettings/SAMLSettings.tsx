import { useForm } from 'react-hook-form';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { LineBreak } from 'shared/elements/LineBreak';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { yupResolver } from '@hookform/resolvers/yup';
import { DEFAULT_SAML_SETTINGS, samlSchema } from './constants';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  deleteOidcSettings,
  downloadSamlCert,
  fetchSamlSettings,
  updateSAMLSettings
} from 'core/API/ssoSettings';
import { Button } from 'shared/elements/Button';
import { AUTH_DEFAULT_VALUES } from '../../constants';
import { parseSAMLFormData } from './utils';
import { Segment } from 'shared/layout/Segment';
import { toast } from 'react-toastify';
import merge from 'lodash/merge';
import Toggle from '@noqdev/cloudscape/toggle';
import { invalidateSsoQueries } from '../utils';

const SAMLSettings = ({ isFetching, current }) => {
  const [formValues, setFormValues] = useState({
    ...AUTH_DEFAULT_VALUES,
    ...DEFAULT_SAML_SETTINGS
  });

  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
    getValues
  } = useForm({
    values: formValues,
    resolver: yupResolver(samlSchema)
  });

  const useMetadataUrl = watch('use_metadata_url');

  const { data: samlSettings, isLoading: isLoadingQuery } = useQuery({
    queryKey: ['samlSettings'],
    queryFn: fetchSamlSettings,
    select: data => data.data
  });

  const downloadMutation = useMutation({
    mutationFn: async () => {
      await downloadSamlCert();
    },
    mutationKey: ['samlDownloadMetadata']
  });

  const { isLoading: isSubmitting, mutateAsync: saveMutation } = useMutation({
    mutationFn: async (data: any) => {
      await updateSAMLSettings(data);
      await deleteOidcSettings();
    },
    mutationKey: ['samlSSOSettings'],
    onSuccess: () => {
      invalidateSsoQueries(queryClient);
      toast.success('Successfully update SAML settings');
    },
    onError: () => {
      toast.error('An error occured, unable update SAML Settings');
    }
  });

  useEffect(() => {
    if (samlSettings?.get_user_by_saml_settings) {
      const use_metadata_url =
        samlSettings?.get_user_by_saml_settings?.idp_metadata_url ?? false;

      const data = merge(
        { ...DEFAULT_SAML_SETTINGS },
        {
          ...samlSettings.get_user_by_saml_settings,
          use_metadata_url
        }
      );

      setFormValues(merge({}, { ...getValues() }, { ...data }));
    }
  }, [getValues, samlSettings?.get_user_by_saml_settings, setValue]);

  const handleSave = handleSubmit(async newSettings => {
    const body = parseSAMLFormData(newSettings);
    if (isValid) {
      await saveMutation(body);
    }
  });

  const isLoading = useMemo(
    () => isSubmitting || isLoadingQuery || isFetching,
    [isSubmitting, isLoadingQuery, isFetching]
  );

  const handleToggleChange = useCallback(checked => {
    setValue('use_metadata_url', checked);
    if (!checked) {
      setValue('idp_metadata_url', '');
    }
  }, []);

  return (
    <Segment isLoading={isLoading}>
      <form onSubmit={handleSave}>
        <Block disableLabelPadding label="Email attribute name" required>
          <Input
            {...register('attributes.email')}
            error={errors?.attributes?.email?.message}
          />
        </Block>
        <LineBreak />

        <Block disableLabelPadding label="Groups attribute name" required>
          <Input
            {...register('attributes.groups')}
            error={errors?.attributes?.groups?.message}
          />
        </Block>
        <LineBreak />
        <Toggle
          checked={useMetadataUrl}
          {...register('use_metadata_url')}
          onChange={({ detail }) => {
            handleToggleChange(detail.checked);
          }}
          name={'use_metadata_url'}
        >
          {' '}
          Use Identity Provider Metadata URL{' '}
        </Toggle>
        <LineBreak />

        {useMetadataUrl && (
          <>
            <Block disableLabelPadding label="IDP Metadata URL" required>
              <Input
                {...register('idp_metadata_url')}
                error={errors?.idp_metadata_url?.message}
              />
            </Block>
            <LineBreak />
          </>
        )}

        {!useMetadataUrl && (
          <>
            <Block disableLabelPadding label="IDP Entity ID" required>
              <Input
                {...register('idp.entityId')}
                name={'idp.entityId'}
                error={errors?.idp?.entityId?.message}
              />
            </Block>
            <LineBreak />

            {/* <Block
              label="Single Sign On Service Binding"
              disableLabelPadding
              required
            >
              <Controller
                name="idp.singleSignOnService.binding"
                control={control}
                render={({ field }) => (
                  <Select
                    name="ssoType"
                    value={watch('idp.singleSignOnService.binding')}
                    onChange={v =>
                      setValue('idp.singleSignOnService.binding', v)
                    }
                    error={Boolean(
                      errors?.idp?.singleSignOnService?.binding?.message
                    )}
                  >
                    {BINDINGS.map(binding => (
                      <SelectOption key={binding} value={binding}>
                        {binding}
                      </SelectOption>
                    ))}
                  </Select>
                )}
              />
            </Block>
            <LineBreak /> */}

            <Block
              disableLabelPadding
              label="Single Sign On Service URL"
              required
            >
              <Input
                {...register('idp.singleSignOnService.url')}
                error={errors?.idp?.singleSignOnService?.url?.message}
              />
            </Block>
            <LineBreak />

            {/* <Block
              label="Single Logout Service Binding"
              disableLabelPadding
              required
            >
              <Controller
                name="idp.singleLogoutService.binding"
                control={control}
                render={({ field }) => (
                  <Select
                    name="singleLogoutService.binding"
                    value={watch('idp.singleLogoutService.binding')}
                    onChange={v =>
                      setValue('idp.singleLogoutService.binding', v)
                    }
                    error={Boolean(
                      errors?.idp?.singleLogoutService?.binding?.message
                    )}
                  >
                    {BINDINGS.map(binding => (
                      <SelectOption key={binding} value={binding}>
                        {binding}
                      </SelectOption>
                    ))}
                  </Select>
                )}
              />
            </Block>
            <LineBreak /> */}

            <Block disableLabelPadding label="Single Logout Service URL">
              <Input
                {...register('idp.singleLogoutService.url')}
                error={errors?.idp?.singleLogoutService?.url?.message}
              />
            </Block>
            <LineBreak />

            <Block disableLabelPadding label="x509cert" required>
              <Input
                {...register('idp.x509cert')}
                error={errors?.idp?.x509cert?.message}
              />
            </Block>
            <LineBreak />

            <Block disableLabelPadding label="SP Entity ID">
              <Input
                {...register('sp.entityId')}
                error={errors?.sp?.entityId && errors?.sp?.entityId?.message}
              />
            </Block>
            <LineBreak />

            {/* <Block disableLabelPadding label="Assertion Consumer Service URL">
              <Input
                {...register('sp.assertionConsumerService.url')}
                error={errors?.sp?.assertionConsumerService?.url?.message}
              />
            </Block>
            <LineBreak /> */}
          </>
        )}

        {/* <Block label="Assertion Consumer Service Binding" disableLabelPadding>
          <Controller
            name="sp.assertionConsumerService.binding"
            control={control}
            render={({ field }) => (
              <Select
                name="assertionConsumerService.binding"
                value={watch('sp.assertionConsumerService.binding')}
                onChange={newValue =>
                  setValue('sp.assertionConsumerService.binding', newValue)
                }
                error={Boolean(
                  errors?.sp?.assertionConsumerService?.binding?.message
                )}
              >
                {BINDINGS.map(binding => (
                  <SelectOption key={binding} value={binding}>
                    {binding}
                  </SelectOption>
                ))}
              </Select>
            )}
          />
        </Block>
        <LineBreak /> */}

        <Button type="submit" disabled={isSubmitting} fullWidth>
          {current ? 'Update' : 'Save'}
        </Button>

        {current && (
          <>
            <Button
              style={{ marginLeft: '10px' }}
              type="button"
              disabled={isSubmitting}
              onClick={async () => await downloadMutation.mutateAsync()}
            >
              Download Cert
            </Button>
            <LineBreak />
          </>
        )}
      </form>
    </Segment>
  );
};

export default SAMLSettings;
