import { yupResolver } from '@hookform/resolvers/yup';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  deleteSamlSettings,
  fetchOidcSettings,
  updateOIDCSettings
} from 'core/API/ssoSettings';
import merge from 'lodash/merge';
import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { toast } from 'react-toastify';
import { Button } from 'shared/elements/Button';
import { LineBreak } from 'shared/elements/LineBreak';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { Checkbox } from 'shared/form/Checkbox';
import { Input } from 'shared/form/Input';
import { transformStringIntoArray } from 'shared/form/Input/utils';
import { Block } from 'shared/layout/Block';
import { Segment } from 'shared/layout/Segment';
import { AUTH_DEFAULT_VALUES } from '../../constants';
import { DEFAULT_OIDC_SETTINGS, oidcSchema } from './constants';
import { parseOIDCFormData } from './utils';
import { Tooltip } from 'shared/elements/Tooltip';
import { Icon } from 'shared/elements/Icon';

const OIDCSettings = ({ isFetching }) => {
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
    formState: { errors, isValid },
    getValues
  } = useForm({
    values: formValues,
    resolver: yupResolver(oidcSchema)
  });

  const { data: oidcSettings, isLoading } = useQuery({
    queryKey: ['oidcSettings'],
    queryFn: fetchOidcSettings,
    select: data => data.data
  });

  const { isLoading: isSubmitting, mutateAsync: saveMutation } = useMutation({
    mutationKey: ['oidcSSOSettings'],
    mutationFn: async (data: any) => {
      await updateOIDCSettings(data);
      await deleteSamlSettings();
      toast.success('Successfully update OIDC settings');
    },
    onError: () => {
      toast.error('An error occured, unable update OIDC Settings');
    }
  });

  useEffect(() => {
    if (oidcSettings?.get_user_by_oidc_settings) {
      const data = merge(
        { ...DEFAULT_OIDC_SETTINGS },
        {
          get_user_by_oidc_settings: oidcSettings?.get_user_by_oidc_settings
        }
      );
      setFormValues(merge({ ...getValues() }, { ...data }));
    }
  }, [getValues, oidcSettings?.get_user_by_oidc_settings, setValue]);

  const handleSave = handleSubmit(async newSettings => {
    const body = parseOIDCFormData(newSettings);
    if (isValid) {
      await saveMutation(body);
    }
  });

  return (
    <Segment isLoading={isSubmitting || isLoading || isFetching}>
      <form onSubmit={handleSave}>
        <LineBreak />
        <Block disableLabelPadding label="Set Secrets" />
        <Checkbox {...register('secrets.use')} />
        {watch('secrets.use') && (
          <>
            <LineBreak />
            <Block disableLabelPadding label="Client ID" required>
              <Input
                {...register('secrets.oidc.client_id')}
                error={errors?.secrets?.oidc?.client_id?.message}
              />
            </Block>

            <LineBreak />
            <Block disableLabelPadding label="Client Secret" required>
              <Input
                {...register('secrets.oidc.client_secret')}
                error={errors?.secrets?.oidc?.client_secret?.message}
              />
            </Block>
          </>
        )}
        <Block disableLabelPadding label="Force Redirect to IP">
          <Checkbox {...register('auth.force_redirect_to_identity_provider')} />
        </Block>
        <Block disableLabelPadding label="Metadata URL" required>
          <Input
            {...register('get_user_by_oidc_settings.metadata_url')}
            error={errors?.get_user_by_oidc_settings?.metadata_url?.message}
          />
        </Block>
        <LineBreak />
        {/* <Input
        type="hidden"
        {...register('get_user_by_oidc_settings.client_scopes')}
      ></Input> */}
        {/* TOOD: add information about how to fill this field (string separated by comma) */}

        <Block disableLabelPadding label="Client Scopes" required>
          <Controller
            control={control}
            name="get_user_by_oidc_settings.client_scopes"
            render={({ field }) => (
              <Tooltip
                text="Client Scopes should be separated by commas"
                alignment="top"
              >
                <div>
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
                    // error={errors?.get_user_by_oidc_settings?.client_scopes?.message}
                    error={errors?.get_user_by_oidc_settings?.client_scopes
                      ?.filter(x => x)
                      .map(x => x.message)
                      .join(',')}
                  />
                </div>
              </Tooltip>
            )}
          />
        </Block>

        <LineBreak />

        <Block disableLabelPadding label="Include Admin Scope">
          <Checkbox
            {...register('get_user_by_oidc_settings.include_admin_scope')}
          />
        </Block>
        <LineBreak />

        <Block disableLabelPadding label="Grant Tpe" required>
          <Input
            {...register('get_user_by_oidc_settings.grant_type')}
            error={errors?.get_user_by_oidc_settings?.grant_type?.message}
          />
        </Block>
        <LineBreak />
        <Block disableLabelPadding label="ID Token Response Key" required>
          <Input
            {...register('get_user_by_oidc_settings.id_token_response_key')}
            error={
              errors?.get_user_by_oidc_settings?.id_token_response_key?.message
            }
          />
        </Block>
        <LineBreak />
        <Block disableLabelPadding label="Access Token Response Key" required>
          <Input
            {...register('get_user_by_oidc_settings.access_token_response_key')}
            error={
              errors?.get_user_by_oidc_settings?.access_token_response_key
                ?.message
            }
          />
        </Block>
        <LineBreak />
        <Block disableLabelPadding label="JWT Email Key" required>
          <Input
            {...register('get_user_by_oidc_settings.jwt_email_key')}
            error={errors?.get_user_by_oidc_settings?.jwt_email_key?.message}
          />
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
            error={
              errors?.get_user_by_oidc_settings?.access_token_audience?.message
            }
          />
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
            error={
              errors?.get_user_by_oidc_settings?.user_info_groups_key?.message
            }
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

export default OIDCSettings;
