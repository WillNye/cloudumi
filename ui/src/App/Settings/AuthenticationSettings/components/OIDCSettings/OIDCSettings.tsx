import { yupResolver } from '@hookform/resolvers/yup';
import { useQuery } from '@tanstack/react-query';
import { fetchOidcSettings } from 'core/API/ssoSettings';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { LineBreak } from 'shared/elements/LineBreak';
import { Checkbox } from 'shared/form/Checkbox';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import {
  AUTH_DEFAULT_VALUES,
  DEFAULT_OIDC_SETTINGS,
  oidcSchema
} from './constants';
import { transformStringIntoArray } from 'shared/form/Input/utils';
import { Button } from 'shared/elements/Button';

const OIDCSettings = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [formValues, setFormValues] = useState({
    ...AUTH_DEFAULT_VALUES,
    ...DEFAULT_OIDC_SETTINGS
  });

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
    resolver: yupResolver(oidcSchema)
  });

  const { data: oidcSettings, ...oidcQuery } = useQuery({
    queryKey: ['oidcSettings'],
    queryFn: fetchOidcSettings,
    select: data => data.data
  });

  return (
    <div>
      <LineBreak />
      <Block disableLabelPadding label="Set Secrets">
        <Checkbox {...register('secrets.use')} />
      </Block>
      {watch('secrets.use') && (
        <>
          <LineBreak />
          <Block disableLabelPadding label="Client ID" required>
            <Input {...register('secrets.oidc.client_id')} />
            {errors?.secrets?.oidc?.client_id.message}
          </Block>

          <LineBreak />
          <Block disableLabelPadding label="Client Secret" required>
            <Input {...register('secrets.oidc.client_secret')} />
            {errors?.secrets?.oidc?.client_secret.message}
          </Block>
        </>
      )}
      <Block disableLabelPadding label="Force Redirect to IP">
        <Checkbox {...register('auth.force_redirect_to_identity_provider')} />
      </Block>
      <Block disableLabelPadding label="Metadata URL" required>
        <Input {...register('get_user_by_oidc_settings.metadata_url')} />
        {errors?.get_user_by_oidc_settings?.metadata_url.message}
      </Block>
      <LineBreak />
      <input
        type="hidden"
        {...register('get_user_by_oidc_settings.client_scopes')}
      ></input>
      {/* TOOD: add information about how to fill this field (string separated by comma) */}
      <Block disableLabelPadding label="Client Scopes" required>
        <Controller
          control={control}
          name="get_user_by_oidc_settings.client_scopes"
          render={({ field }) => (
            <Input
              onChange={e =>
                setValue(
                  'get_user_by_oidc_settings.client_scopes',
                  transformStringIntoArray.output(e)
                )
              }
              value={transformStringIntoArray.input(
                watch('get_user_by_oidc_settings.client_scopes')
              )}
            />
          )}
        />
        {errors?.get_user_by_oidc_settings?.client_scopes.message}

        {errors?.get_user_by_oidc_settings?.client_scopes
          ?.filter(x => x)
          .map(x => x.message)
          .join(',')}
      </Block>

      <LineBreak />

      <Block disableLabelPadding label="Include Admin Scope">
        <Checkbox
          {...register('get_user_by_oidc_settings.include_admin_scope')}
        />
      </Block>
      <LineBreak />

      <Block disableLabelPadding label="Grant Tpe" required>
        <Input {...register('get_user_by_oidc_settings.grant_type')} />

        {errors?.get_user_by_oidc_settings?.grant_type.message}
      </Block>
      <LineBreak />
      <Block disableLabelPadding label="ID Token Response Key" required>
        <Input
          {...register('get_user_by_oidc_settings.id_token_response_key')}
        />

        {errors?.get_user_by_oidc_settings?.id_token_response_key.message}
      </Block>
      <LineBreak />
      <Block disableLabelPadding label="Access Token Response Key" required>
        <Input
          {...register('get_user_by_oidc_settings.access_token_response_key')}
        />

        {errors?.get_user_by_oidc_settings?.access_token_response_key.message}
      </Block>
      <LineBreak />
      <Block disableLabelPadding label="JWT Email Key" required>
        <Input {...register('get_user_by_oidc_settings.jwt_email_key')} />
        {errors?.get_user_by_oidc_settings?.jwt_email_key?.message}
      </Block>
      <LineBreak />
      <Block disableLabelPadding label="Enable MFA">
        <Checkbox {...register('get_user_by_oidc_settings.enable_mfa')} />
      </Block>
      <Block disableLabelPadding label="Get Groups from Access Token">
        <Checkbox
          {...register(
            'get_user_by_oidc_settings.get_groups_from_access_token'
          )}
        />
      </Block>
      <Block disableLabelPadding label="Audience" required>
        <Input
          {...register('get_user_by_oidc_settings.access_token_audience')}
        />
        {errors?.get_user_by_oidc_settings?.access_token_audience?.message}
      </Block>
      <LineBreak />
      <Block disableLabelPadding label="Get Groups from UserInfo Endpoint">
        <Checkbox
          {...register(
            'get_user_by_oidc_settings.get_groups_from_userinfo_endpoint'
          )}
        />
      </Block>
      <Block disableLabelPadding label="User Groups Key" required>
        <Input
          {...register('get_user_by_oidc_settings.user_info_groups_key')}
        />
        {errors?.get_user_by_oidc_settings?.user_info_groups_key.message}
      </Block>
      <LineBreak />
      <Button type="submit" disabled={isSubmitting} fullWidth>
        Save
      </Button>
      <LineBreak />
    </div>
  );
};

export default OIDCSettings;
