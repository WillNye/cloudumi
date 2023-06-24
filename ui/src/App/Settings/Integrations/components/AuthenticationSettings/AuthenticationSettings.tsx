import React, { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import {
  fetchOidcSettings,
  fetchSamlSettings,
  updateOIDCSettings,
  updateSAMLSettings,
  deleteOidcSettings,
  deleteSamlSettings
} from 'core/API/ssoSettings';
import { yupResolver } from '@hookform/resolvers/yup';
import * as Yup from 'yup';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { Segment } from 'shared/layout/Segment';
import { Select, SelectOption } from 'shared/form/Select';
import { Button } from 'shared/elements/Button';
import { Checkbox } from 'shared/form/Checkbox';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { LineBreak } from 'shared/elements/LineBreak';

// SAML Bindings: https://en.wikipedia.org/wiki/SAML_2.0#Bindings
const BINDINGS = [
  'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
  'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
];

// TODO: Check if oidc.secrets.use is editable or not, if it is create editable=no (default true), if it is update editable=yes
// TODO: which component for multiselect? because for client_scopes we need to select multiple but in a suggestion way?
// other components needs the same

// TODO: continue with SAML form
// TODO: invalidate queries on delete, on upsert

// TODO: detect when secrets.oidc are required
// the idea is detect if the user SHOULD HAVE TO add secrets.
// if oidc settings are being created, secrets are required

const REDACTED_STR = '********';

const AuthenticationSettings = () => {
  const schema = Yup.object()
    .shape({
      ssoType: Yup.string()
        .oneOf(['none', 'oidc', 'saml'])
        .required('Required'),
      auth: Yup.object()
        .shape({
          extra_auth_cookies: Yup.array()
            .of(Yup.string())
            .default([])
            .nullable(),
          force_redirect_to_identity_provider: Yup.boolean().default(false),
          challenge_url: Yup.object().shape({
            enabled: Yup.boolean().default(true)
          }),
          logout_redirect_url: Yup.string().url().default('')
        })
        .when('ssoType', {
          is: type => type != 'none',
          then: schema => schema.required(),
          otherwise: schema => schema.notRequired()
        }),
      oidc: Yup.object()
        .shape({
          get_user_by_oidc_settings: Yup.object().shape({
            metadata_url: Yup.string().default(''),
            client_scopes: Yup.array().of(Yup.string()).default([]),
            include_admin_scope: Yup.boolean().default(false),
            grant_type: Yup.string().default('authorization_code'),
            id_token_response_key: Yup.string().default('id_token'),
            access_token_response_key: Yup.string().default('access_token'),
            jwt_email_key: Yup.string().default('email'),
            enable_mfa: Yup.boolean().default(false),
            get_groups_from_access_token: Yup.boolean().default(false),
            access_token_audience: Yup.string().default(''),
            get_groups_from_userinfo_endpoint: Yup.boolean().default(false),
            user_info_groups_key: Yup.string().default('groups')
          }),
          secrets: Yup.object().shape({
            use: Yup.boolean().default(false),
            oidc: Yup.object().shape({
              client_id: Yup.string().when('use', {
                is: true,
                then: schema => schema.required(),
                otherwise: schema => schema.notRequired()
              }),
              client_secret: Yup.string().when('use', {
                is: true,
                then: schema => schema.required(),
                otherwise: schema => schema.notRequired()
              })
            })
          })
        })
        .when('ssoType', {
          is: 'oidc',
          then: schema => schema.required(),
          otherwise: schema => schema.notRequired()
        })
        .nullable()
      // saml: Yup.object()
      //   .shape({
      //     get_user_by_saml_settings: Yup.object().shape({
      //       jwt: Yup.object().shape({
      //         expiration_hours: Yup.number().default(1),
      //         email_key: Yup.string().default('email'),
      //         group_key: Yup.string().default('groups')
      //       }),
      //       attributes: Yup.object().shape({
      //         user: Yup.string().default('user'),
      //         groups: Yup.string().default('groups'),
      //         email: Yup.string().default('email')
      //       }),
      //       idp_metadata_url: Yup.string().default('').notRequired(),
      //       idp: Yup.object()
      //         .shape({
      //           entityId: Yup.string().required(),
      //           singleSignOnService: Yup.object()
      //             .shape({
      //               binding: Yup.string()
      //                 .oneOf(BINDINGS)
      //                 .default(BINDINGS[0])
      //                 .required(),
      //               url: Yup.string().url().required()
      //             })
      //             .notRequired(),
      //           singleLogoutService: Yup.object()
      //             .shape({
      //               binding: Yup.string()
      //                 .oneOf(BINDINGS)
      //                 .default(BINDINGS[0])
      //                 .required(),
      //               url: Yup.string().url().required()
      //             })
      //             .notRequired(),
      //           x509cert: Yup.string().required()
      //         })
      //         .when('idp_metadata_url', {
      //           is: (idp_metadata_url: string) => idp_metadata_url != '',
      //           then: schema => schema.required(),
      //           otherwise: schema => schema.notRequired()
      //         }),
      //       sp: Yup.object()
      //         .shape({
      //           assertionConsumerService: Yup.object().shape({
      //             binding: Yup.string()
      //               .oneOf(BINDINGS)
      //               .default(BINDINGS[0])
      //               .required(),
      //             url: Yup.string().url().required()
      //           }),
      //           entityId: Yup.string().required()
      //         })
      //         .notRequired()
      //     })
      //   })
      //   .when('ssoType', {
      //     is: 'saml',
      //     then: schema => schema.required(),
      //     otherwise: schema => schema.notRequired()
      //   })
    })
    .required();

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const queryClient = useQueryClient();
  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    setValue,
    trigger,
    formState: { isSubmitting, errors }
  } = useForm({
    defaultValues: {
      ssoType: 'none',
      auth: {
        force_redirect_to_identity_provider: false,
        extra_auth_cookies: ['AWSELBAuthSessionCookie'],
        challenge_url: { enabled: false },
        logout_redirect_url: ''
      },
      oidc: {
        get_user_by_oidc_settings: {
          metadata_url: '',
          client_scopes: [],
          include_admin_scope: false,
          grant_type: 'authorization_code',
          id_token_response_key: 'id_token',
          access_token_response_key: 'access_token',
          jwt_email_key: 'email',
          enable_mfa: false,
          get_groups_from_access_token: true,
          access_token_audience: '',
          get_groups_from_userinfo_endpoint: true,
          user_info_groups_key: 'groups'
        },
        secrets: {
          use: false,
          oidc: {
            client_id: '',
            client_secret: ''
          }
        }
      },
      saml: null
    },
    resolver: yupResolver(schema)
  });

  console.log(errors);

  // watch sso provider type
  const ssoType = watch('ssoType');

  const { data: oidcSettings, ...oidcQuery } = useQuery({
    queryKey: ['oidcSettings'],
    queryFn: fetchOidcSettings,
    select: data => data.data
  });

  const { data: samlSettings, ...samlQuery } = useQuery({
    queryKey: ['samlSettings'],
    queryFn: fetchSamlSettings,
    select: data => data.data
  });

  useEffect(() => {
    if (
      oidcSettings?.auth.get_user_by_saml ||
      samlSettings?.auth.get_user_by_saml
    ) {
      setValue('ssoType', 'saml');
    } else if (
      oidcSettings?.auth.get_user_by_oidc ||
      samlSettings?.auth.get_user_by_oidc
    ) {
      setValue('ssoType', 'oidc');
    } else {
      setValue('ssoType', 'none');
    }
  }, [oidcSettings, samlSettings]);
  // FIXME: how to fix it? or just skip it?
  // React Hook useEffect has a missing dependency: 'setValue'.

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (ssoType === 'oidc') {
        await deleteSamlSettings();
      } else if (ssoType === 'saml') {
        await deleteOidcSettings();
      } else if (ssoType === 'none') {
        await deleteOidcSettings();
        await deleteSamlSettings();
      }
    },
    mutationKey: ['deleteSsoSettings'],
    onSuccess: () => {
      // TODO: invalidate queries on delete
      // if (ssoType === 'none') {
      //   queryClient.invalidateQueries(`samlSettings`);
      //   queryClient.invalidateQueries(`oidcSettings`);
      // } else {
      //   queryClient.invalidateQueries(`${ssoType}Settings`);
      // }

      reset();
    }
  });

  const { isLoading: isLoadingSave, mutateAsync: saveMutation } = useMutation({
    mutationFn: async (data: any) => {
      if (ssoType === 'oidc') {
        await updateOIDCSettings(data);
      } else if (ssoType === 'saml') {
        await updateSAMLSettings(data);
      } else if (ssoType === 'none') {
        await deleteMutation.mutateAsync();
      }
    },
    mutationKey: ['ssoSettings'],
    onSuccess: () => {
      // TODO: invalidate queries
      //queryClient.invalidateQueries(`${idpType}Settings`)
    }
  });

  useEffect(() => {
    if (samlQuery.isLoading || oidcQuery.isLoading) {
      setIsLoading(true);
    } else {
      setIsLoading(false);
    }
  }, [
    samlQuery.isLoading,
    oidcQuery.isLoading,
    deleteMutation.isLoading,
    isLoadingSave
  ]);

  const handleSave = handleSubmit(async newSettings => {
    await saveMutation(newSettings);
  });

  return (
    <Segment isLoading={isLoading}>
      {errorMessage && (
        <Notification
          type={NotificationType.ERROR}
          header={errorMessage}
          showCloseIcon={false}
          fullWidth
        />
      )}
      {successMessage && (
        <Notification
          type={NotificationType.SUCCESS}
          header={successMessage}
          showCloseIcon={false}
          fullWidth
        />
      )}

      <form onSubmit={handleSave}>
        <Block label="SSO" disableLabelPadding required>
          <Controller
            name="ssoType"
            control={control}
            render={({ field }) => (
              <Select
                name="ssoType"
                value={watch('ssoType')}
                onChange={v => setValue('ssoType', v)}
              >
                <SelectOption value="none">Not use SSO</SelectOption>
                <SelectOption value="oidc">OpenID Connect</SelectOption>
                <SelectOption value="saml">SAML</SelectOption>
              </Select>
            )}
          />
          {errors.ssoType && errors.ssoType.message}
        </Block>
        <LineBreak />

        {ssoType === 'none' && <></>}
        {ssoType === 'oidc' && (
          <>
            <LineBreak />
            <Block disableLabelPadding label="Set Secrets">
              <Checkbox {...register('oidc.secrets.use')} />
              <div>{/* Generate form fields from oidcSettings */}</div>
            </Block>
            {watch('oidc.secrets.use') && (
              <>
                <LineBreak />
                <Block disableLabelPadding label="Client ID" required>
                  <Input {...register('oidc.secrets.oidc.client_id')} />
                </Block>

                <LineBreak />
                <Block disableLabelPadding label="Client Secret" required>
                  <Input {...register('oidc.secrets.oidc.client_secret')} />
                </Block>
              </>
            )}
            <Block disableLabelPadding label="Force Redirect to IP">
              <Checkbox
                {...register('auth.force_redirect_to_identity_provider')}
              />
            </Block>
            {watch('oidc.get_user_by_oidc_settings.metadata_url')}
            <Block disableLabelPadding label="Metadata URL" required>
              <Input
                {...register('oidc.get_user_by_oidc_settings.metadata_url')}
              />
            </Block>
            <LineBreak />
            client_scopes
            <Block disableLabelPadding label="Include Admin Scope">
              <Checkbox
                {...register(
                  'oidc.get_user_by_oidc_settings.include_admin_scope'
                )}
              />
            </Block>
            <Block disableLabelPadding label="Grant Tpe" required>
              <Input
                {...register('oidc.get_user_by_oidc_settings.grant_type')}
              />
            </Block>
            <LineBreak />
            <Block disableLabelPadding label="ID Token Response Key" required>
              <Input
                {...register(
                  'oidc.get_user_by_oidc_settings.id_token_response_key'
                )}
              />
            </Block>
            <LineBreak />
            <Block
              disableLabelPadding
              label="Access Token Response Key"
              required
            >
              <Input
                {...register(
                  'oidc.get_user_by_oidc_settings.access_token_response_key'
                )}
              />
            </Block>
            <LineBreak />
            <Block disableLabelPadding label="JWT Email Key" required>
              <Input
                {...register('oidc.get_user_by_oidc_settings.jwt_email_key')}
              />
            </Block>
            <LineBreak />
            <Block disableLabelPadding label="Enable MFA">
              <Checkbox
                {...register('oidc.get_user_by_oidc_settings.enable_mfa')}
              />
            </Block>
            <Block disableLabelPadding label="Get Groups from Access Token">
              <Checkbox
                {...register(
                  'oidc.get_user_by_oidc_settings.get_groups_from_access_token'
                )}
              />
            </Block>
            <Block disableLabelPadding label="Audience" required>
              <Input
                {...register(
                  'oidc.get_user_by_oidc_settings.access_token_audience'
                )}
              />
            </Block>
            <LineBreak />
            <Block
              disableLabelPadding
              label="Get Groups from UserInfo Endpoint"
            >
              <Checkbox
                {...register(
                  'oidc.get_user_by_oidc_settings.get_groups_from_userinfo_endpoint'
                )}
              />
            </Block>
            <Block disableLabelPadding label="User Groups Key" required>
              <Input
                {...register(
                  'oidc.get_user_by_oidc_settings.user_info_groups_key'
                )}
              />
            </Block>
            <LineBreak />
          </>
        )}
        {ssoType === 'saml' && (
          <div>{/* Generate form fields from samlSettings */}</div>
        )}
        <Button type="submit" disabled={isSubmitting}>
          Save
        </Button>
      </form>
    </Segment>
  );
};

export default AuthenticationSettings;
