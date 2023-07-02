import { Controller, useForm } from 'react-hook-form';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { LineBreak } from 'shared/elements/LineBreak';
import { useState } from 'react';
import { Select, SelectOption } from 'shared/form/Select';
import { yupResolver } from '@hookform/resolvers/yup';
import { BINDINGS, DEFAULT_SAML_SETTINGS, samlSchema } from './constants';
import { useQuery } from '@tanstack/react-query';
import { fetchSamlSettings } from 'core/API/ssoSettings';
import { Button } from 'shared/elements/Button';

const SAMLSettings = () => {
  const [formValues, setFormValues] = useState(DEFAULT_SAML_SETTINGS);

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { isSubmitting, errors, isValid },
    getValues
  } = useForm({
    values: formValues,
    resolver: yupResolver(samlSchema)
  });

  const { data: samlSettings, ...samlQuery } = useQuery({
    queryKey: ['samlSettings'],
    queryFn: fetchSamlSettings,
    select: data => data.data
  });

  return (
    <div>
      <Block disableLabelPadding label="Attributes User" required>
        <Input {...register('attributes.user')} />
        {errors?.attributes?.user?.message}
      </Block>
      <LineBreak />

      <Block disableLabelPadding label="Attributes email" required>
        <Input {...register('attributes.email')} />
        {errors?.attributes?.email?.message}
      </Block>
      <LineBreak />

      <Block disableLabelPadding label="Attributes groups" required>
        <Input {...register('attributes.groups')} />
        {errors?.attributes?.groups?.message}
      </Block>
      <LineBreak />

      <Block disableLabelPadding label="idp_metadata_url" required>
        <Input {...register('idp_metadata_url')} />
        {errors?.idp_metadata_url?.message}
      </Block>
      <LineBreak />
      {!watch('idp_metadata_url') && (
        <>
          <Block disableLabelPadding label="IDP Entity ID" required>
            <Input {...register('idp.entityId')} />
            {errors?.idp?.entityId?.message}
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
                  onChange={v => setValue('idp.singleSignOnService.binding', v)}
                >
                  {BINDINGS.map(binding => (
                    <SelectOption key={binding} value={binding}>
                      {binding}
                    </SelectOption>
                  ))}
                </Select>
              )}
            />
            {errors?.idp?.singleSignOnService.binding.message}
          </Block>
          <LineBreak />

          <Block
            disableLabelPadding
            label="Single Sign On Service URL"
            required
          >
            <Input {...register('idp.singleSignOnService.url')} />
            {errors?.idp?.singleSignOnService.url?.message}
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
                  onChange={v => setValue('idp.singleLogoutService.binding', v)}
                >
                  {BINDINGS.map(binding => (
                    <SelectOption key={binding} value={binding}>
                      {binding}
                    </SelectOption>
                  ))}
                </Select>
              )}
            />
            {errors?.idp?.singleLogoutService?.binding.message}
          </Block>
          <LineBreak />

          <Block disableLabelPadding label="Single Logout Service URL" required>
            <Input {...register('idp.singleLogoutService.url')} />
            {errors?.idp?.singleLogoutService.url?.message}
          </Block>
          <LineBreak />

          <Block disableLabelPadding label="x509cert" required>
            <Input {...register('idp.x509cert')} />
            {errors?.idp?.x509cert?.message}
          </Block>
          <LineBreak />
        </>
      )}

      <Block disableLabelPadding label="SP Entity ID">
        <Input {...register('sp.entityId')} />
        {errors?.sp?.entityId && errors?.sp?.entityId?.message}
      </Block>
      <LineBreak />

      <Block disableLabelPadding label="Assertion Consumer Service URL">
        <Input {...register('sp.assertionConsumerService.url')} />
        {errors?.idp?.singleLogoutService.url &&
          errors?.idp?.singleLogoutService?.url?.message}
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
            >
              {BINDINGS.map(binding => (
                <SelectOption key={binding} value={binding}>
                  {binding}
                </SelectOption>
              ))}
            </Select>
          )}
        />
        {errors?.sp?.assertionConsumerService?.binding.message}
      </Block>
      <LineBreak />
      <Button type="submit" disabled={isSubmitting} fullWidth>
        Save
      </Button>
      <LineBreak />
    </div>
  );
};

export default SAMLSettings;
