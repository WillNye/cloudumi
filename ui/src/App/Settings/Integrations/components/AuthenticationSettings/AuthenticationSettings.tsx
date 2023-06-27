import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Controller, useForm } from 'react-hook-form';
import {
  fetchOidcSettings,
  fetchSamlSettings,
  updateOIDCSettings,
  updateSAMLSettings,
  deleteOidcSettings,
  deleteSamlSettings,
  fetchOidcWellKnownConfig
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
import { debounce, merge } from 'lodash';

// SAML Bindings: https://en.wikipedia.org/wiki/SAML_2.0#Bindings
const BINDINGS = [
  'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
  'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
];

const OKTA_SCOPES = [
  'groups',
  'openid',
  'profile',
  'email',
  'address',
  'phone',
  'offline_access',
  'device_sso'
];

const AUTH0_SCOPES = [
  'openid',
  'profile',
  'offline_access',
  'name',
  'given_name',
  'family_name',
  'nickname',
  'email',
  'email_verified',
  'picture',
  'created_at',
  'identities',
  'phone',
  'address'
];

const AZURE_SCOPES = ['openid', 'profile', 'email', 'offline_access'];

// TODO: which component for multiselect? because for client_scopes we need to select multiple but in a suggestion way?
// TODO: continue with SAML form

const DEFAULT_OIDC_SETTINGS = {
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
  }
};

const DEFAULT_SAML_SETTINGS = {
  saml: {
    get_user_by_saml_settings: {
      jwt: {
        expiration_hours: 2,
        email_key: 'email',
        group_key: 'groups'
      },
      attributes: {
        user: 'user',
        groups: 'groups',
        email: 'email'
      },
      idp_metadata_url: '',
      sp: {
        entityId: '',
        assertionConsumerService: {
          binding: '',
          url: ''
        }
      },
      idp: {
        entityId: '',
        singleSignOnService: {
          binding: '',
          url: ''
        },
        singleLogoutService: {
          binding: '',
          url: ''
        },
        x509cert: ''
      }
    }
  }
};

const AUTH_DEFAULT_VALUES = {
  auth: {
    force_redirect_to_identity_provider: false,
    extra_auth_cookies: ['AWSELBAuthSessionCookie'],
    challenge_url: { enabled: false },
    logout_redirect_url: ''
  }
};

// eslint-disable-next-line complexity
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
      oidc: Yup.object().when('ssoType', {
        is: 'oidc',
        then: schema =>
          schema
            .shape({
              get_user_by_oidc_settings: Yup.object().shape({
                metadata_url: Yup.string().url().default(''),
                client_scopes: Yup.array().of(Yup.string()).default([]),
                include_admin_scope: Yup.boolean().default(false),
                grant_type: Yup.string()
                  .default('authorization_code')
                  .required(),
                id_token_response_key: Yup.string()
                  .default('id_token')
                  .required(),
                access_token_response_key: Yup.string()
                  .default('access_token')
                  .required(),
                jwt_email_key: Yup.string().default('email').required(),
                enable_mfa: Yup.boolean().default(false),
                get_groups_from_access_token: Yup.boolean().default(false),
                access_token_audience: Yup.string().required(),
                get_groups_from_userinfo_endpoint: Yup.boolean().default(false),
                user_info_groups_key: Yup.string().default('groups').required()
              }),
              secrets: Yup.object().shape({
                use: Yup.boolean().default(false),
                oidc: Yup.object().when('use', {
                  is: true,
                  then: schema =>
                    schema.shape({
                      client_id: Yup.string().required().min(1),
                      client_secret: Yup.string().required().min(1)
                    })
                })
              })
            })
            .required(),
        otherwise: schema => schema.notRequired()
      }),
      saml: Yup.object().when('ssoType', {
        is: 'saml',
        then: schema =>
          schema
            .shape({
              get_user_by_saml_settings: Yup.object().shape({
                idp_metadata_url: Yup.string().url().default(''),
                jwt: Yup.object().shape({
                  expiration_hours: Yup.number().default(1),
                  email_key: Yup.string().default('email'),
                  group_key: Yup.string().default('groups')
                }),
                attributes: Yup.object().shape({
                  user: Yup.string().default('user'),
                  groups: Yup.string().default('groups'),
                  email: Yup.string().default('email')
                }),
                idp: Yup.object().when('idp_metadata_url', {
                  is: (idp_metadata_url: string) => !idp_metadata_url,
                  then: schema =>
                    schema
                      .shape({
                        entityId: Yup.string().required(),
                        singleSignOnService: Yup.object()
                          .shape({
                            binding: Yup.string()
                              .oneOf(BINDINGS)
                              .default(BINDINGS[0])
                              .required(),
                            url: Yup.string().url().required()
                          })
                          .notRequired(),
                        singleLogoutService: Yup.object()
                          .shape({
                            binding: Yup.string()
                              .oneOf(BINDINGS)
                              .default(BINDINGS[0])
                              .required(),
                            url: Yup.string().url().required()
                          })
                          .notRequired(),
                        x509cert: Yup.string().required()
                      })
                      .required(),
                  otherwise: schema => schema.notRequired()
                }),
                sp: Yup.object()
                  .shape({
                    assertionConsumerService: Yup.object().shape({
                      binding: Yup.string()
                        .oneOf([...BINDINGS, '', null])
                        .default('')
                        .notRequired(),
                      url: Yup.string().url().notRequired()
                    }),
                    entityId: Yup.string()
                  })
                  .notRequired()
              })
            })
            .required(),
        otherwise: schema => schema.notRequired()
      })
    })
    .required();

  // TODO: remove or use?
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // available client scopes when metadata_url is set
  const [clientScopesOptions, setClientScopesOptions] = useState<string[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const queryClient = useQueryClient();
  const [formValues, setFormValues] = useState({
    ssoType: 'none',
    ...AUTH_DEFAULT_VALUES,
    ...DEFAULT_OIDC_SETTINGS,
    ...DEFAULT_SAML_SETTINGS
  });

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    setError,
    clearErrors,
    formState: { isSubmitting, errors, isValid },
    getValues
  } = useForm({
    values: formValues,
    resolver: yupResolver(schema)
  });

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

  /**
   * Fetches the well-known config from the given url and sets the client scopes options.
   * if not available, sets the client scopes options to the default scopes (azure, okta, auth0).
   */
  const onChangeOidcMetadataUrl = debounce(async (v: string) => {
    if (!v) {
      setClientScopesOptions([]);
      clearErrors('oidc.get_user_by_oidc_settings.metadata_url');
      return;
    }

    const data = await fetchOidcWellKnownConfig(v).catch(console.error);

    if (data) {
      setClientScopesOptions(data['scopes_supported']);
      clearErrors('oidc.get_user_by_oidc_settings.metadata_url');
    } else if (v.includes('microsoft')) {
      setClientScopesOptions(AZURE_SCOPES);
      clearErrors('oidc.get_user_by_oidc_settings.metadata_url');
    } else if (v.includes('okta')) {
      setClientScopesOptions(OKTA_SCOPES);
      clearErrors('oidc.get_user_by_oidc_settings.metadata_url');
    } else if (v.includes('auth0')) {
      setClientScopesOptions(AUTH0_SCOPES);
      clearErrors('oidc.get_user_by_oidc_settings.metadata_url');
    } else {
      setError('oidc.get_user_by_oidc_settings.metadata_url', {
        message: 'URL is not a valid OIDC metadata URL'
      });
    }
  }, 500);

  useEffect(() => {
    onChangeOidcMetadataUrl(
      watch('oidc.get_user_by_oidc_settings.metadata_url')
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watch('oidc.get_user_by_oidc_settings.metadata_url')]);

  // Get Current SSO type (without edition, source of truth)
  const getCurrentSsoType = useCallback(() => {
    if (
      oidcSettings?.auth.get_user_by_saml ||
      samlSettings?.auth.get_user_by_saml
    ) {
      return 'saml';
    } else if (
      oidcSettings?.auth.get_user_by_oidc ||
      samlSettings?.auth.get_user_by_oidc
    ) {
      return 'oidc';
    } else {
      return 'none';
    }
  }, [oidcSettings?.auth, samlSettings?.auth]);

  // Get Current SSO type (with edition)
  const editMode = useMemo(() => {
    if (ssoType != getCurrentSsoType()) {
      return true;
    } else {
      return false;
    }
  }, [getCurrentSsoType, ssoType]);

  useEffect(() => {
    if (editMode && ssoType == 'oidc') {
      setValue('oidc.secrets.use', true);
    } else {
      setValue('oidc.secrets.use', false);
    }
  }, [ssoType, editMode, setValue]);

  useEffect(() => {
    setValue('ssoType', getCurrentSsoType());
  }, [getCurrentSsoType, setValue]);

  useEffect(() => {
    if (oidcSettings?.get_user_by_oidc_settings) {
      const data = merge(
        {},
        { ...DEFAULT_OIDC_SETTINGS },
        {
          oidc: {
            get_user_by_oidc_settings: oidcSettings?.get_user_by_oidc_settings
          }
        }
      );
      setFormValues(merge({ ...getValues() }, { ...data }));
    }
  }, [getValues, oidcSettings?.get_user_by_oidc_settings, setValue]);

  useEffect(() => {
    if (samlSettings?.get_user_by_saml_settings) {
      const data = merge(
        {},
        { ...DEFAULT_SAML_SETTINGS },
        {
          saml: {
            get_user_by_saml_settings: samlSettings.get_user_by_saml_settings
          }
        }
      );

      setFormValues(merge({}, { ...getValues() }, { ...data }));
    }
  }, [getValues, samlSettings?.get_user_by_saml_settings, setValue]);

  const { isLoading: isLoadingSave, mutateAsync: saveMutation } = useMutation({
    mutationFn: async (data: any) => {
      if (ssoType === 'oidc') {
        await updateOIDCSettings(data);
        await deleteSamlSettings();
      } else if (ssoType === 'saml') {
        await updateSAMLSettings(data);
        await deleteOidcSettings();
      } else if (ssoType === 'none') {
        await deleteOidcSettings();
        await deleteSamlSettings();
      }
    },
    mutationKey: ['ssoSettings'],
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`samlSettings`] });
      queryClient.invalidateQueries({ queryKey: [`oidcSettings`] });

      setSuccessMessage('Settings saved successfully');
    }
  });

  useEffect(() => {
    if (samlQuery.isLoading || oidcQuery.isLoading) {
      setIsLoading(true);
    } else {
      setIsLoading(false);
    }
  }, [samlQuery.isLoading, oidcQuery.isLoading, isLoadingSave]);

  /**
   * Parse body to save settings
   * @param settings
   * @returns
   */
  const parseBody = settings => {
    if (ssoType == 'oidc') {
      const secrets = settings?.oidc?.secrets?.use
        ? {
            secrets: {
              oidc: {
                ...settings.oidc.secrets.oidc
              }
            }
          }
        : {};

      const get_user_by_oidc_settings = {
        get_user_by_oidc_settings: {
          metadata_url: settings.oidc.get_user_by_oidc_settings.metadata_url,
          client_scopes: settings.oidc.get_user_by_oidc_settings.client_scopes,
          include_admin_scope:
            settings.oidc.get_user_by_oidc_settings.include_admin_scope,
          grant_type: settings.oidc.get_user_by_oidc_settings.grant_type,
          id_token_response_key:
            settings.oidc.get_user_by_oidc_settings.id_token_response_key,
          access_token_response_key:
            settings.oidc.get_user_by_oidc_settings.access_token_response_key,
          jwt_email_key: settings.oidc.get_user_by_oidc_settings.jwt_email_key,
          enable_mfa: settings.oidc.get_user_by_oidc_settings.enable_mfa,
          get_groups_from_access_token:
            settings.oidc.get_user_by_oidc_settings
              .get_groups_from_access_token,
          access_token_audience:
            settings.oidc.get_user_by_oidc_settings.access_token_audience,
          get_groups_from_userinfo_endpoint:
            settings.oidc.get_user_by_oidc_settings
              .get_groups_from_userinfo_endpoint,
          user_info_groups_key:
            settings.oidc.get_user_by_oidc_settings.user_info_groups_key
        }
      };

      const auth = {
        auth: {
          get_user_by_oidc: true,
          get_user_by_saml: false,
          extra_auth_cookies: settings.auth.extra_auth_cookies,
          force_redirect_to_identity_provider:
            settings.auth.force_redirect_to_identity_provider
        }
      };

      return {
        ...get_user_by_oidc_settings,
        ...secrets,
        ...auth
      };
    } else if (ssoType == 'saml') {
      const get_user_by_saml_settings = {
        get_user_by_saml_settings: {
          jwt: {
            expiration_hours: 2
          },
          attributes: {
            user: settings.saml.get_user_by_saml_settings.attributes.user,
            groups: settings.saml.get_user_by_saml_settings.attributes.groups,
            email: settings.saml.get_user_by_saml_settings.attributes.email
          },
          idp_metadata_url:
            settings.saml.get_user_by_saml_settings.idp_metadata_url ?? null,
          // if idp_metadata_url is not set, use idp object
          ...(!settings.saml.get_user_by_saml_settings.idp_metadata_url
            ? {
                idp: {
                  entityId:
                    settings.saml.get_user_by_saml_settings.idp.entityId,
                  singleSignOnService: {
                    binding:
                      settings.saml.get_user_by_saml_settings.idp
                        .singleSignOnService.binding,
                    url: settings.saml.get_user_by_saml_settings.idp
                      .singleSignOnService.url
                  },
                  singleLogoutService: {
                    binding:
                      settings.saml.get_user_by_saml_settings.idp
                        .singleLogoutService.binding,
                    url: settings.saml.get_user_by_saml_settings.idp
                      .singleLogoutService.url
                  },
                  x509cert: settings.saml.get_user_by_saml_settings.idp.x509cert
                }
              }
            : { idp: null }),
          // if sp is not set, then set it to null
          sp: {
            // if entityId is not set, then set it to null
            ...(settings.saml.get_user_by_saml_settings.sp.entityId && {
              entityId: settings.saml.get_user_by_saml_settings.sp.entityId
            }),
            // if assertionConsumerService is not set, then set it to null
            ...(settings.saml.get_user_by_saml_settings.sp
              .assertionConsumerService
              ? {
                  assertionConsumerService: {
                    binding:
                      settings.saml.get_user_by_saml_settings.sp
                        .assertionConsumerService.binding,
                    url: settings.saml.get_user_by_saml_settings.sp
                      .assertionConsumerService.url
                  }
                }
              : { sp: null })
          }
        }
      };

      const auth = {
        auth: {
          get_user_by_oidc: false,
          get_user_by_saml: true,
          extra_auth_cookies: settings.auth.extra_auth_cookies,
          force_redirect_to_identity_provider:
            settings.auth.force_redirect_to_identity_provider
        }
      };

      return {
        ...get_user_by_saml_settings,
        ...auth
      };
    } else {
      return null;
    }
  };

  const handleSave = handleSubmit(async newSettings => {
    const body = parseBody(newSettings);
    if (isValid) {
      await saveMutation(body);
    }
  });

  return (
    <Segment isLoading={isLoading}>
      {errorMessage && (
        <Notification
          type={NotificationType.ERROR}
          header={errorMessage}
          showCloseIcon={true}
          onClose={() => setErrorMessage(null)}
          fullWidth
        />
      )}
      {successMessage && (
        <Notification
          type={NotificationType.SUCCESS}
          header={successMessage}
          showCloseIcon={true}
          onClose={() => setSuccessMessage(null)}
          fullWidth
        />
      )}

      <LineBreak />

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
            </Block>
            {watch('oidc.secrets.use') && (
              <>
                <LineBreak />
                <Block disableLabelPadding label="Client ID" required>
                  <Input {...register('oidc.secrets.oidc.client_id')} />
                  {errors?.oidc?.secrets?.oidc?.client_id &&
                    errors?.oidc?.secrets?.oidc?.client_id.message}
                </Block>

                <LineBreak />
                <Block disableLabelPadding label="Client Secret" required>
                  <Input {...register('oidc.secrets.oidc.client_secret')} />
                  {errors?.oidc?.secrets?.oidc?.client_secret &&
                    errors?.oidc?.secrets?.oidc?.client_secret.message}
                </Block>
              </>
            )}
            <Block disableLabelPadding label="Force Redirect to IP">
              <Checkbox
                {...register('auth.force_redirect_to_identity_provider')}
              />
            </Block>
            <Block disableLabelPadding label="Metadata URL" required>
              <Input
                {...register('oidc.get_user_by_oidc_settings.metadata_url')}
              />
              {errors?.oidc?.get_user_by_oidc_settings?.metadata_url &&
                errors?.oidc?.get_user_by_oidc_settings?.metadata_url.message}
            </Block>
            <LineBreak />
            <Controller
              name="oidc.get_user_by_oidc_settings.client_scopes"
              control={control}
              render={({ field }) => (
                <Block disableLabelPadding label="Client Scopes" required>
                  <Select
                    multiple={true}
                    closeOnSelect={false}
                    name="oidc.get_user_by_oidc_settings.client_scopes"
                    value={watch(
                      'oidc.get_user_by_oidc_settings.client_scopes'
                    )}
                    onChange={v =>
                      setValue(
                        'oidc.get_user_by_oidc_settings.client_scopes',
                        v
                      )
                    }
                  >
                    {clientScopesOptions.map(cs => (
                      <SelectOption key={cs} value={cs}>
                        {cs}
                      </SelectOption>
                    ))}
                  </Select>
                </Block>
              )}
            />
            <LineBreak />

            <Block disableLabelPadding label="Include Admin Scope">
              <Checkbox
                {...register(
                  'oidc.get_user_by_oidc_settings.include_admin_scope'
                )}
              />
            </Block>
            <LineBreak />

            <Block disableLabelPadding label="Grant Tpe" required>
              <Input
                {...register('oidc.get_user_by_oidc_settings.grant_type')}
              />

              {errors?.oidc?.get_user_by_oidc_settings?.grant_type &&
                errors?.oidc?.get_user_by_oidc_settings?.grant_type.message}
            </Block>
            <LineBreak />
            <Block disableLabelPadding label="ID Token Response Key" required>
              <Input
                {...register(
                  'oidc.get_user_by_oidc_settings.id_token_response_key'
                )}
              />

              {errors?.oidc?.get_user_by_oidc_settings?.id_token_response_key &&
                errors?.oidc?.get_user_by_oidc_settings?.id_token_response_key
                  .message}
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

              {errors?.oidc?.get_user_by_oidc_settings
                ?.access_token_response_key &&
                errors?.oidc?.get_user_by_oidc_settings
                  ?.access_token_response_key.message}
            </Block>
            <LineBreak />
            <Block disableLabelPadding label="JWT Email Key" required>
              <Input
                {...register('oidc.get_user_by_oidc_settings.jwt_email_key')}
              />
              {errors?.oidc?.get_user_by_oidc_settings?.jwt_email_key &&
                errors?.oidc?.get_user_by_oidc_settings?.jwt_email_key?.message}
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
              {errors?.oidc?.get_user_by_oidc_settings?.access_token_audience &&
                errors?.oidc?.get_user_by_oidc_settings?.access_token_audience
                  ?.message}
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
              {errors?.oidc?.get_user_by_oidc_settings?.user_info_groups_key &&
                errors?.oidc?.get_user_by_oidc_settings?.user_info_groups_key
                  .message}
            </Block>
            <LineBreak />
          </>
        )}
        {ssoType === 'saml' && (
          <>
            <Block disableLabelPadding label="Attributes User" required>
              <Input
                {...register('saml.get_user_by_saml_settings.attributes.user')}
              />
              {errors?.saml?.get_user_by_saml_settings?.attributes?.user &&
                errors?.saml?.get_user_by_saml_settings?.attributes?.user
                  ?.message}
            </Block>
            <LineBreak />

            <Block disableLabelPadding label="Attributes email" required>
              <Input
                {...register('saml.get_user_by_saml_settings.attributes.email')}
              />
              {errors?.saml?.get_user_by_saml_settings?.attributes?.email &&
                errors?.saml?.get_user_by_saml_settings?.attributes?.email
                  ?.message}
            </Block>
            <LineBreak />

            <Block disableLabelPadding label="Attributes groups" required>
              <Input
                {...register(
                  'saml.get_user_by_saml_settings.attributes.groups'
                )}
              />
              {errors?.saml?.get_user_by_saml_settings?.attributes?.groups &&
                errors?.saml?.get_user_by_saml_settings?.attributes?.groups
                  ?.message}
            </Block>
            <LineBreak />

            <Block disableLabelPadding label="idp_metadata_url" required>
              <Input
                {...register('saml.get_user_by_saml_settings.idp_metadata_url')}
              />
              {
                errors?.saml?.get_user_by_saml_settings?.idp_metadata_url
                  ?.message
              }
            </Block>
            <LineBreak />
            {!watch('saml.get_user_by_saml_settings.idp_metadata_url') && (
              <>
                <Block disableLabelPadding label="IDP Entity ID" required>
                  <Input
                    {...register('saml.get_user_by_saml_settings.idp.entityId')}
                  />
                  {errors?.saml?.get_user_by_saml_settings?.idp?.entityId &&
                    errors?.saml?.get_user_by_saml_settings?.idp?.entityId
                      ?.message}
                </Block>
                <LineBreak />

                <Block
                  label="Single Sign On Service Binding"
                  disableLabelPadding
                  required
                >
                  <Controller
                    name="saml.get_user_by_saml_settings.idp.singleSignOnService.binding"
                    control={control}
                    render={({ field }) => (
                      <Select
                        name="ssoType"
                        value={watch(
                          'saml.get_user_by_saml_settings.idp.singleSignOnService.binding'
                        )}
                        onChange={v =>
                          setValue(
                            'saml.get_user_by_saml_settings.idp.singleSignOnService.binding',
                            v
                          )
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
                  {errors?.saml?.get_user_by_saml_settings?.idp
                    ?.singleSignOnService.binding &&
                    errors?.saml?.get_user_by_saml_settings?.idp
                      ?.singleSignOnService.binding.message}
                </Block>
                <LineBreak />

                <Block
                  disableLabelPadding
                  label="Single Sign On Service URL"
                  required
                >
                  <Input
                    {...register(
                      'saml.get_user_by_saml_settings.idp.singleSignOnService.url'
                    )}
                  />
                  {errors?.saml?.get_user_by_saml_settings?.idp
                    ?.singleSignOnService.url &&
                    errors?.saml?.get_user_by_saml_settings?.idp
                      ?.singleSignOnService.url?.message}
                </Block>
                <LineBreak />

                <Block
                  label="Single Logout Service Binding"
                  disableLabelPadding
                  required
                >
                  <Controller
                    name="saml.get_user_by_saml_settings.idp.singleLogoutService.binding"
                    control={control}
                    render={({ field }) => (
                      <Select
                        name="singleLogoutService.binding"
                        value={watch(
                          'saml.get_user_by_saml_settings.idp.singleLogoutService.binding'
                        )}
                        onChange={v =>
                          setValue(
                            'saml.get_user_by_saml_settings.idp.singleLogoutService.binding',
                            v
                          )
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
                  {errors?.saml?.get_user_by_saml_settings?.idp
                    ?.singleLogoutService?.binding &&
                    errors?.saml?.get_user_by_saml_settings?.idp
                      ?.singleLogoutService?.binding.message}
                </Block>
                <LineBreak />

                <Block
                  disableLabelPadding
                  label="Single Logout Service URL"
                  required
                >
                  <Input
                    {...register(
                      'saml.get_user_by_saml_settings.idp.singleLogoutService.url'
                    )}
                  />
                  {errors?.saml?.get_user_by_saml_settings?.idp
                    ?.singleLogoutService.url &&
                    errors?.saml?.get_user_by_saml_settings?.idp
                      ?.singleLogoutService.url?.message}
                </Block>
                <LineBreak />

                <Block disableLabelPadding label="x509cert" required>
                  <Input
                    {...register('saml.get_user_by_saml_settings.idp.x509cert')}
                  />
                  {errors?.saml?.get_user_by_saml_settings?.idp?.x509cert &&
                    errors?.saml?.get_user_by_saml_settings?.idp?.x509cert
                      ?.message}
                </Block>
                <LineBreak />
              </>
            )}

            <Block disableLabelPadding label="SP Entity ID">
              <Input
                {...register('saml.get_user_by_saml_settings.sp.entityId')}
              />
              {errors?.saml?.get_user_by_saml_settings?.sp?.entityId &&
                errors?.saml?.get_user_by_saml_settings?.sp?.entityId?.message}
            </Block>
            <LineBreak />

            <Block disableLabelPadding label="Assertion Consumer Service URL">
              <Input
                {...register(
                  'saml.get_user_by_saml_settings.sp.assertionConsumerService.url'
                )}
              />
              {errors?.saml?.get_user_by_saml_settings?.idp?.singleLogoutService
                .url &&
                errors?.saml?.get_user_by_saml_settings?.idp
                  ?.singleLogoutService?.url?.message}
            </Block>
            <LineBreak />

            <Block
              label="Assertion Consumer Service Binding"
              disableLabelPadding
            >
              <Controller
                name="saml.get_user_by_saml_settings.sp.assertionConsumerService.binding"
                control={control}
                render={({ field }) => (
                  <Select
                    name="assertionConsumerService.binding"
                    value={watch(
                      'saml.get_user_by_saml_settings.sp.assertionConsumerService.binding'
                    )}
                    onChange={v =>
                      setValue(
                        'saml.get_user_by_saml_settings.sp.assertionConsumerService.binding',
                        v
                      )
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
              {errors?.saml?.get_user_by_saml_settings?.sp
                ?.assertionConsumerService?.binding &&
                errors?.saml?.get_user_by_saml_settings?.sp
                  ?.assertionConsumerService?.binding.message}
            </Block>
          </>
        )}
        <Button type="submit" disabled={isSubmitting}>
          Save
        </Button>
      </form>
    </Segment>
  );
};

export default AuthenticationSettings;
