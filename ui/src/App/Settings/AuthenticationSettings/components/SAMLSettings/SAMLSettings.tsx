import { Controller, useForm } from 'react-hook-form';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { LineBreak } from 'shared/elements/LineBreak';
import { useEffect, useState } from 'react';
import { Select, SelectOption } from 'shared/form/Select';
import { yupResolver } from '@hookform/resolvers/yup';
import { BINDINGS, DEFAULT_SAML_SETTINGS, samlSchema } from './constants';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  deleteOidcSettings,
  fetchSamlSettings,
  updateSAMLSettings
} from 'core/API/ssoSettings';
import { Button } from 'shared/elements/Button';
import { AUTH_DEFAULT_VALUES } from '../../constants';
import { parseSAMLFormData } from './utils';
import { Segment } from 'shared/layout/Segment';
import { toast } from 'react-toastify';
import merge from 'lodash/merge';

const SAMLSettings = ({ isFetching }) => {
  const [formValues, setFormValues] = useState({
    ...AUTH_DEFAULT_VALUES,
    ...DEFAULT_SAML_SETTINGS
  });

  const queryClient = useQueryClient();

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
    getValues
  } = useForm({
    values: formValues,
    resolver: yupResolver(samlSchema)
  });

  const { data: samlSettings, isLoading } = useQuery({
    queryKey: ['samlSettings'],
    queryFn: fetchSamlSettings,
    select: data => data.data
  });

  const { isLoading: isSubmitting, mutateAsync: saveMutation } = useMutation({
    mutationFn: async (data: any) => {
      await updateSAMLSettings(data);
      await deleteOidcSettings();
    },
    mutationKey: ['samlSSOSettings'],
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`samlSettings`] });
      queryClient.invalidateQueries({ queryKey: [`oidcSettings`] });
      toast.success('Successfully update SAML settings');
    },
    onError: () => {
      toast.error('An error occured, unable update SAML Settings');
    }
  });

  useEffect(() => {
    if (samlSettings?.get_user_by_saml_settings) {
      const data = merge(
        { ...DEFAULT_SAML_SETTINGS },
        {
          ...samlSettings.get_user_by_saml_settings
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

  return (
    <Segment isLoading={isSubmitting || isLoading || isFetching}>
      <form onSubmit={handleSave}>
        <Block disableLabelPadding label="Attributes User" required>
          <Input
            {...register('attributes.user')}
            error={errors?.attributes?.user?.message}
          />
        </Block>
        <LineBreak />

        <Block disableLabelPadding label="Attributes email" required>
          <Input
            {...register('attributes.email')}
            error={errors?.attributes?.email?.message}
          />
        </Block>
        <LineBreak />

        <Block disableLabelPadding label="Attributes groups" required>
          <Input
            {...register('attributes.groups')}
            error={errors?.attributes?.groups?.message}
          />
        </Block>
        <LineBreak />

        <Block disableLabelPadding label="idp_metadata_url" required>
          <Input
            {...register('idp_metadata_url')}
            error={errors?.idp_metadata_url?.message}
          />
        </Block>
        <LineBreak />
        {!watch('idp_metadata_url') && (
          <>
            <Block disableLabelPadding label="IDP Entity ID" required>
              <Input
                {...register('idp.entityId')}
                error={errors?.idp?.entityId?.message}
              />
            </Block>
            <LineBreak />

            <Block
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
            <LineBreak />

            <Block
              disableLabelPadding
              label="Single Sign On Service URL"
              required
            >
              <Input
                {...register('idp.singleSignOnService.url')}
                error={errors?.idp?.singleSignOnService.url?.message}
              />
            </Block>
            <LineBreak />
            <Block
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
            <LineBreak />

            <Block
              disableLabelPadding
              label="Single Logout Service URL"
              required
            >
              <Input
                {...register('idp.singleLogoutService.url')}
                error={errors?.idp?.singleLogoutService.url?.message}
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
          </>
        )}

        <Block disableLabelPadding label="SP Entity ID">
          <Input
            {...register('sp.entityId')}
            error={errors?.sp?.entityId && errors?.sp?.entityId?.message}
          />
        </Block>
        <LineBreak />

        <Block disableLabelPadding label="Assertion Consumer Service URL">
          <Input
            {...register('sp.assertionConsumerService.url')}
            error={errors?.idp?.singleLogoutService?.url?.message}
          />
        </Block>
        <LineBreak />

        <Block label="Assertion Consumer Service Binding" disableLabelPadding>
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
        <LineBreak />
        <Button type="submit" disabled={isSubmitting} fullWidth>
          Save
        </Button>
        <LineBreak />
      </form>
    </Segment>
  );
};

export default SAMLSettings;
