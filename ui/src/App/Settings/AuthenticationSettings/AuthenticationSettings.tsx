import { Fragment, useEffect, useMemo, useState } from 'react';
import { AUTH_SETTINGS_TABS } from './constants';
import SAMLSettings from './components/SAMLSettings';
import OIDCSettings from './components/OIDCSettings';
import styles from './AuthenticationSettings.module.css';
import { Button } from 'shared/elements/Button';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  deleteOidcSettings,
  deleteSamlSettings,
  fetchAuthSettings
} from 'core/API/ssoSettings';
import { toast } from 'react-toastify';

// // eslint-disable-next-line complexity
// const AuthenticationSettings = () => {
//   const [errorMessage, setErrorMessage] = useState<string | null>(null);
//   const [successMessage, setSuccessMessage] = useState<string | null>(null);

//   const [isLoading, setIsLoading] = useState(false);
//   const queryClient = useQueryClient();
//   const [formValues, setFormValues] = useState({
//     ssoType: 'none',
//     ...AUTH_DEFAULT_VALUES,
//     ...DEFAULT_OIDC_SETTINGS,
//     ...DEFAULT_SAML_SETTINGS
//   });

//   const {
//     register,
//     control,
//     handleSubmit,
//     watch,
//     setValue,
//     formState: { isSubmitting, errors, isValid },
//     getValues
//   } = useForm({
//     values: formValues,
//     resolver: yupResolver(schema)
//   });

//   const ssoType = watch('ssoType');

//   const { data: oidcSettings, ...oidcQuery } = useQuery({
//     queryKey: ['oidcSettings'],
//     queryFn: fetchOidcSettings,
//     select: data => data.data
//   });

//   const { data: samlSettings, ...samlQuery } = useQuery({
//     queryKey: ['samlSettings'],
//     queryFn: fetchSamlSettings,
//     select: data => data.data
//   });

//   // Get Current SSO type (source of truth)
//   const getCurrentSsoType = useCallback(() => {
//     if (
//       oidcSettings?.auth.get_user_by_saml ||
//       samlSettings?.auth.get_user_by_saml
//     ) {
//       return 'saml';
//     } else if (
//       oidcSettings?.auth.get_user_by_oidc ||
//       samlSettings?.auth.get_user_by_oidc
//     ) {
//       return 'oidc';
//     } else {
//       return 'none';
//     }
//   }, [oidcSettings?.auth, samlSettings?.auth]);

//   // Get Current SSO type (during edition)
//   const upsertMode = useMemo(() => {
//     if (ssoType != getCurrentSsoType()) {
//       return true;
//     } else {
//       return false;
//     }
//   }, [getCurrentSsoType, ssoType]);

//   // If SSO type is OIDC and it is creating the OIDC settings, set the value of the checkbox to true
//   // to force adding the secrets
//   useEffect(() => {
//     if (upsertMode && ssoType == 'oidc') {
//       setValue('oidc.secrets.use', true);
//     } else {
//       setValue('oidc.secrets.use', false);
//     }
//   }, [ssoType, upsertMode, setValue]);

//   // update SSO type depending on the current server data
//   useEffect(() => {
//     setValue('ssoType', getCurrentSsoType());
//   }, [getCurrentSsoType, setValue]);

//   // update OIDC current settings
//   useEffect(() => {
//     if (oidcSettings?.get_user_by_oidc_settings) {
//       const data = merge(
//         {},
//         { ...DEFAULT_OIDC_SETTINGS },
//         {
//           oidc: {
//             get_user_by_oidc_settings: oidcSettings?.get_user_by_oidc_settings
//           }
//         }
//       );
//       setFormValues(merge({ ...getValues() }, { ...data }));
//     }
//   }, [getValues, oidcSettings?.get_user_by_oidc_settings, setValue]);

//   // update OIDC current settings
//   useEffect(() => {
//     if (samlSettings?.get_user_by_saml_settings) {
//       const data = merge(
//         {},
//         { ...DEFAULT_SAML_SETTINGS },
//         {
//           saml: {
//             get_user_by_saml_settings: samlSettings.get_user_by_saml_settings
//           }
//         }
//       );

//       setFormValues(merge({}, { ...getValues() }, { ...data }));
//     }
//   }, [getValues, samlSettings?.get_user_by_saml_settings, setValue]);

//   const { isLoading: isLoadingSave, mutateAsync: saveMutation } = useMutation({
//     mutationFn: async (data: any) => {
//       if (ssoType === 'oidc') {
//         await updateOIDCSettings(data);
//         await deleteSamlSettings();
//       } else if (ssoType === 'saml') {
//         await updateSAMLSettings(data);
//         await deleteOidcSettings();
//       } else if (ssoType === 'none') {
//         await deleteOidcSettings();
//         await deleteSamlSettings();
//       }
//     },
//     mutationKey: ['ssoSettings'],
//     onSuccess: () => {
//       queryClient.invalidateQueries({ queryKey: [`samlSettings`] });
//       queryClient.invalidateQueries({ queryKey: [`oidcSettings`] });

//       setSuccessMessage('Settings saved successfully');
//     }
//   });

//   // Loading effect should be shown when queries or mutations are loading, or when queries are fetching.
//   useEffect(() => {
//     if (
//       samlQuery.isLoading ||
//       oidcQuery.isLoading ||
//       oidcQuery.isFetching ||
//       samlQuery.isFetching
//     ) {
//       setIsLoading(true);
//     } else {
//       setIsLoading(false);
//     }
//   }, [
//     samlQuery.isLoading,
//     oidcQuery.isLoading,
//     isLoadingSave,
//     oidcQuery.isFetching,
//     samlQuery.isFetching
//   ]);

//   const handleSave = handleSubmit(async newSettings => {
//     const body = parseSsoSettingsBody(newSettings, ssoType);
//     if (isValid) {
//       await saveMutation(body);
//     }
//   });

//   return (
//     <Segment isLoading={isLoading}>
//       {errorMessage && (
//         <Notification
//           type={NotificationType.ERROR}
//           header={errorMessage}
//           showCloseIcon={true}
//           onClose={() => setErrorMessage(null)}
//           fullWidth
//         />
//       )}
//       {successMessage && (
//         <Notification
//           type={NotificationType.SUCCESS}
//           header={successMessage}
//           showCloseIcon={true}
//           onClose={() => setSuccessMessage(null)}
//           fullWidth
//         />
//       )}

//       <LineBreak />

//       <form onSubmit={handleSave}>
//         <Block label="SSO" disableLabelPadding required>
//           <Controller
//             name="ssoType"
//             control={control}
//             render={({ field }) => (
//               <Select
//                 name="ssoType"
//                 value={watch('ssoType')}
//                 onChange={v => setValue('ssoType', v)}
//               >
//                 <SelectOption value="none">SSO not configured</SelectOption>
//                 <SelectOption value="oidc">OpenID Connect</SelectOption>
//                 <SelectOption value="saml">SAML</SelectOption>
//               </Select>
//             )}
//           />
//           {errors.ssoType && errors.ssoType.message}
//         </Block>
//         <LineBreak />

//         {ssoType === 'none' && <></>}
//         {ssoType === 'oidc' && (
//           <>
//             <LineBreak />
//             <Block disableLabelPadding label="Set Secrets">
//               <Checkbox {...register('oidc.secrets.use')} />
//             </Block>
//             {watch('oidc.secrets.use') && (
//               <>
//                 <LineBreak />
//                 <Block disableLabelPadding label="Client ID" required>
//                   <Input {...register('oidc.secrets.oidc.client_id')} />
//                   {errors?.oidc?.secrets?.oidc?.client_id &&
//                     errors?.oidc?.secrets?.oidc?.client_id.message}
//                 </Block>

//                 <LineBreak />
//                 <Block disableLabelPadding label="Client Secret" required>
//                   <Input {...register('oidc.secrets.oidc.client_secret')} />
//                   {errors?.oidc?.secrets?.oidc?.client_secret &&
//                     errors?.oidc?.secrets?.oidc?.client_secret.message}
//                 </Block>
//               </>
//             )}
//             <Block disableLabelPadding label="Force Redirect to IP">
//               <Checkbox
//                 {...register('auth.force_redirect_to_identity_provider')}
//               />
//             </Block>
//             <Block disableLabelPadding label="Metadata URL" required>
//               <Input
//                 {...register('oidc.get_user_by_oidc_settings.metadata_url')}
//               />
//               {errors?.oidc?.get_user_by_oidc_settings?.metadata_url &&
//                 errors?.oidc?.get_user_by_oidc_settings?.metadata_url.message}
//             </Block>
//             <LineBreak />
//             <input
//               type="hidden"
//               {...register('oidc.get_user_by_oidc_settings.client_scopes')}
//             ></input>
//             {/* TOOD: add information about how to fill this field (string separated by comma) */}
//             <Block disableLabelPadding label="Client Scopes" required>
//               <Controller
//                 control={control}
//                 name="oidc.get_user_by_oidc_settings.client_scopes"
//                 render={({ field }) => (
//                   <Input
//                     onChange={e =>
//                       setValue(
//                         'oidc.get_user_by_oidc_settings.client_scopes',
//                         transformStringIntoArray.output(e)
//                       )
//                     }
//                     value={transformStringIntoArray.input(
//                       watch('oidc.get_user_by_oidc_settings.client_scopes')
//                     )}
//                   />
//                 )}
//               />
//               {errors?.oidc?.get_user_by_oidc_settings?.client_scopes &&
//                 errors?.oidc?.get_user_by_oidc_settings?.client_scopes.message}

//               {errors?.oidc?.get_user_by_oidc_settings?.client_scopes &&
//                 errors?.oidc?.get_user_by_oidc_settings?.client_scopes
//                   ?.filter(x => x)
//                   .map(x => x.message)
//                   .join(',')}
//             </Block>

//             <LineBreak />

//             <Block disableLabelPadding label="Include Admin Scope">
//               <Checkbox
//                 {...register(
//                   'oidc.get_user_by_oidc_settings.include_admin_scope'
//                 )}
//               />
//             </Block>
//             <LineBreak />

//             <Block disableLabelPadding label="Grant Tpe" required>
//               <Input
//                 {...register('oidc.get_user_by_oidc_settings.grant_type')}
//               />

//               {errors?.oidc?.get_user_by_oidc_settings?.grant_type &&
//                 errors?.oidc?.get_user_by_oidc_settings?.grant_type.message}
//             </Block>
//             <LineBreak />
//             <Block disableLabelPadding label="ID Token Response Key" required>
//               <Input
//                 {...register(
//                   'oidc.get_user_by_oidc_settings.id_token_response_key'
//                 )}
//               />

//               {errors?.oidc?.get_user_by_oidc_settings?.id_token_response_key &&
//                 errors?.oidc?.get_user_by_oidc_settings?.id_token_response_key
//                   .message}
//             </Block>
//             <LineBreak />
//             <Block
//               disableLabelPadding
//               label="Access Token Response Key"
//               required
//             >
//               <Input
//                 {...register(
//                   'oidc.get_user_by_oidc_settings.access_token_response_key'
//                 )}
//               />

//               {errors?.oidc?.get_user_by_oidc_settings
//                 ?.access_token_response_key &&
//                 errors?.oidc?.get_user_by_oidc_settings
//                   ?.access_token_response_key.message}
//             </Block>
//             <LineBreak />
//             <Block disableLabelPadding label="JWT Email Key" required>
//               <Input
//                 {...register('oidc.get_user_by_oidc_settings.jwt_email_key')}
//               />
//               {errors?.oidc?.get_user_by_oidc_settings?.jwt_email_key &&
//                 errors?.oidc?.get_user_by_oidc_settings?.jwt_email_key?.message}
//             </Block>
//             <LineBreak />
//             <Block disableLabelPadding label="Enable MFA">
//               <Checkbox
//                 {...register('oidc.get_user_by_oidc_settings.enable_mfa')}
//               />
//             </Block>
//             <Block disableLabelPadding label="Get Groups from Access Token">
//               <Checkbox
//                 {...register(
//                   'oidc.get_user_by_oidc_settings.get_groups_from_access_token'
//                 )}
//               />
//             </Block>
//             <Block disableLabelPadding label="Audience" required>
//               <Input
//                 {...register(
//                   'oidc.get_user_by_oidc_settings.access_token_audience'
//                 )}
//               />
//               {errors?.oidc?.get_user_by_oidc_settings?.access_token_audience &&
//                 errors?.oidc?.get_user_by_oidc_settings?.access_token_audience
//                   ?.message}
//             </Block>
//             <LineBreak />
//             <Block
//               disableLabelPadding
//               label="Get Groups from UserInfo Endpoint"
//             >
//               <Checkbox
//                 {...register(
//                   'oidc.get_user_by_oidc_settings.get_groups_from_userinfo_endpoint'
//                 )}
//               />
//             </Block>
//             <Block disableLabelPadding label="User Groups Key" required>
//               <Input
//                 {...register(
//                   'oidc.get_user_by_oidc_settings.user_info_groups_key'
//                 )}
//               />
//               {errors?.oidc?.get_user_by_oidc_settings?.user_info_groups_key &&
//                 errors?.oidc?.get_user_by_oidc_settings?.user_info_groups_key
//                   .message}
//             </Block>
//             <LineBreak />
//           </>
//         )}
//         {ssoType === 'saml' && (
//           <>
//             <Block disableLabelPadding label="Attributes User" required>
//               <Input
//                 {...register('saml.get_user_by_saml_settings.attributes.user')}
//               />
//               {errors?.saml?.get_user_by_saml_settings?.attributes?.user &&
//                 errors?.saml?.get_user_by_saml_settings?.attributes?.user
//                   ?.message}
//             </Block>
//             <LineBreak />

//             <Block disableLabelPadding label="Attributes email" required>
//               <Input
//                 {...register('saml.get_user_by_saml_settings.attributes.email')}
//               />
//               {errors?.saml?.get_user_by_saml_settings?.attributes?.email &&
//                 errors?.saml?.get_user_by_saml_settings?.attributes?.email
//                   ?.message}
//             </Block>
//             <LineBreak />

//             <Block disableLabelPadding label="Attributes groups" required>
//               <Input
//                 {...register(
//                   'saml.get_user_by_saml_settings.attributes.groups'
//                 )}
//               />
//               {errors?.saml?.get_user_by_saml_settings?.attributes?.groups &&
//                 errors?.saml?.get_user_by_saml_settings?.attributes?.groups
//                   ?.message}
//             </Block>
//             <LineBreak />

//             <Block disableLabelPadding label="idp_metadata_url" required>
//               <Input
//                 {...register('saml.get_user_by_saml_settings.idp_metadata_url')}
//               />
//               {
//                 errors?.saml?.get_user_by_saml_settings?.idp_metadata_url
//                   ?.message
//               }
//             </Block>
//             <LineBreak />
//             {!watch('saml.get_user_by_saml_settings.idp_metadata_url') && (
//               <>
//                 <Block disableLabelPadding label="IDP Entity ID" required>
//                   <Input
//                     {...register('saml.get_user_by_saml_settings.idp.entityId')}
//                   />
//                   {errors?.saml?.get_user_by_saml_settings?.idp?.entityId &&
//                     errors?.saml?.get_user_by_saml_settings?.idp?.entityId
//                       ?.message}
//                 </Block>
//                 <LineBreak />

//                 <Block
//                   label="Single Sign On Service Binding"
//                   disableLabelPadding
//                   required
//                 >
//                   <Controller
//                     name="saml.get_user_by_saml_settings.idp.singleSignOnService.binding"
//                     control={control}
//                     render={({ field }) => (
//                       <Select
//                         name="ssoType"
//                         value={watch(
//                           'saml.get_user_by_saml_settings.idp.singleSignOnService.binding'
//                         )}
//                         onChange={v =>
//                           setValue(
//                             'saml.get_user_by_saml_settings.idp.singleSignOnService.binding',
//                             v
//                           )
//                         }
//                       >
//                         {BINDINGS.map(binding => (
//                           <SelectOption key={binding} value={binding}>
//                             {binding}
//                           </SelectOption>
//                         ))}
//                       </Select>
//                     )}
//                   />
//                   {errors?.saml?.get_user_by_saml_settings?.idp
//                     ?.singleSignOnService.binding &&
//                     errors?.saml?.get_user_by_saml_settings?.idp
//                       ?.singleSignOnService.binding.message}
//                 </Block>
//                 <LineBreak />

//                 <Block
//                   disableLabelPadding
//                   label="Single Sign On Service URL"
//                   required
//                 >
//                   <Input
//                     {...register(
//                       'saml.get_user_by_saml_settings.idp.singleSignOnService.url'
//                     )}
//                   />
//                   {errors?.saml?.get_user_by_saml_settings?.idp
//                     ?.singleSignOnService.url &&
//                     errors?.saml?.get_user_by_saml_settings?.idp
//                       ?.singleSignOnService.url?.message}
//                 </Block>
//                 <LineBreak />

//                 <Block
//                   label="Single Logout Service Binding"
//                   disableLabelPadding
//                   required
//                 >
//                   <Controller
//                     name="saml.get_user_by_saml_settings.idp.singleLogoutService.binding"
//                     control={control}
//                     render={({ field }) => (
//                       <Select
//                         name="singleLogoutService.binding"
//                         value={watch(
//                           'saml.get_user_by_saml_settings.idp.singleLogoutService.binding'
//                         )}
//                         onChange={v =>
//                           setValue(
//                             'saml.get_user_by_saml_settings.idp.singleLogoutService.binding',
//                             v
//                           )
//                         }
//                       >
//                         {BINDINGS.map(binding => (
//                           <SelectOption key={binding} value={binding}>
//                             {binding}
//                           </SelectOption>
//                         ))}
//                       </Select>
//                     )}
//                   />
//                   {errors?.saml?.get_user_by_saml_settings?.idp
//                     ?.singleLogoutService?.binding &&
//                     errors?.saml?.get_user_by_saml_settings?.idp
//                       ?.singleLogoutService?.binding.message}
//                 </Block>
//                 <LineBreak />

//                 <Block
//                   disableLabelPadding
//                   label="Single Logout Service URL"
//                   required
//                 >
//                   <Input
//                     {...register(
//                       'saml.get_user_by_saml_settings.idp.singleLogoutService.url'
//                     )}
//                   />
//                   {errors?.saml?.get_user_by_saml_settings?.idp
//                     ?.singleLogoutService.url &&
//                     errors?.saml?.get_user_by_saml_settings?.idp
//                       ?.singleLogoutService.url?.message}
//                 </Block>
//                 <LineBreak />

//                 <Block disableLabelPadding label="x509cert" required>
//                   <Input
//                     {...register('saml.get_user_by_saml_settings.idp.x509cert')}
//                   />
//                   {errors?.saml?.get_user_by_saml_settings?.idp?.x509cert &&
//                     errors?.saml?.get_user_by_saml_settings?.idp?.x509cert
//                       ?.message}
//                 </Block>
//                 <LineBreak />
//               </>
//             )}

//             <Block disableLabelPadding label="SP Entity ID">
//               <Input
//                 {...register('saml.get_user_by_saml_settings.sp.entityId')}
//               />
//               {errors?.saml?.get_user_by_saml_settings?.sp?.entityId &&
//                 errors?.saml?.get_user_by_saml_settings?.sp?.entityId?.message}
//             </Block>
//             <LineBreak />

//             <Block disableLabelPadding label="Assertion Consumer Service URL">
//               <Input
//                 {...register(
//                   'saml.get_user_by_saml_settings.sp.assertionConsumerService.url'
//                 )}
//               />
//               {errors?.saml?.get_user_by_saml_settings?.idp?.singleLogoutService
//                 .url &&
//                 errors?.saml?.get_user_by_saml_settings?.idp
//                   ?.singleLogoutService?.url?.message}
//             </Block>
//             <LineBreak />

//             <Block
//               label="Assertion Consumer Service Binding"
//               disableLabelPadding
//             >
//               <Controller
//                 name="saml.get_user_by_saml_settings.sp.assertionConsumerService.binding"
//                 control={control}
//                 render={({ field }) => (
//                   <Select
//                     name="assertionConsumerService.binding"
//                     value={watch(
//                       'saml.get_user_by_saml_settings.sp.assertionConsumerService.binding'
//                     )}
//                     onChange={v =>
//                       setValue(
//                         'saml.get_user_by_saml_settings.sp.assertionConsumerService.binding',
//                         v
//                       )
//                     }
//                   >
//                     {BINDINGS.map(binding => (
//                       <SelectOption key={binding} value={binding}>
//                         {binding}
//                       </SelectOption>
//                     ))}
//                   </Select>
//                 )}
//               />
//               {errors?.saml?.get_user_by_saml_settings?.sp
//                 ?.assertionConsumerService?.binding &&
//                 errors?.saml?.get_user_by_saml_settings?.sp
//                   ?.assertionConsumerService?.binding.message}
//             </Block>
//           </>
//         )}
//         <Button type="submit" disabled={isSubmitting}>
//           Save
//         </Button>
//       </form>
//     </Segment>
//   );
// };

// export default AuthenticationSettings;

const AuthenticationSettings = () => {
  const [currentTab, setCurrentTab] = useState<AUTH_SETTINGS_TABS>(
    AUTH_SETTINGS_TABS.SAML
  );
  const queryClient = useQueryClient();

  const { data: authSettings, ...authQuery } = useQuery({
    queryKey: ['authSettings'],
    queryFn: fetchAuthSettings,
    select: data => data.data
  });

  const { isLoading, mutateAsync: saveMutation } = useMutation({
    mutationFn: async () => {
      await deleteOidcSettings();
      await deleteSamlSettings();
    },
    mutationKey: ['removeAuthSettings'],
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`samlSettings`] });
      queryClient.invalidateQueries({ queryKey: [`oidcSettings`] });
      toast.success('Successfully removed SAML/OIDC Settings');
    },
    onError: () => {
      toast.error('An error occured, unable remove SAML/OIDC Settings');
    }
  });

  const content = useMemo(() => {
    if (currentTab === AUTH_SETTINGS_TABS.OIDC) {
      return <OIDCSettings isFetching={isLoading} />;
    }

    if (currentTab === AUTH_SETTINGS_TABS.SAML) {
      return <SAMLSettings isFetching={isLoading} />;
    }

    return <Fragment />;
  }, [currentTab, isLoading]);

  useEffect(() => {
    if (authSettings?.get_user_by_saml) {
      setCurrentTab(AUTH_SETTINGS_TABS.SAML);
    } else if (authSettings?.get_user_by_oidc) {
      setCurrentTab(AUTH_SETTINGS_TABS.OIDC);
    }
  }, [authSettings]);

  return (
    <div className={styles.container}>
      <div className={styles.remove}>
        <Button
          onClick={() => saveMutation()}
          color="secondary"
          variant="outline"
          disabled={isLoading}
        >
          Deactivate
        </Button>
      </div>
      <div>
        <nav className={styles.nav}>
          <ul className={styles.navList}>
            <li
              className={`${styles.navItem} ${
                currentTab === AUTH_SETTINGS_TABS.SAML && styles.isActive
              }`}
              onClick={() => setCurrentTab(AUTH_SETTINGS_TABS.SAML)}
            >
              <div className={styles.text}>SAML Settings</div>
            </li>
            <li
              className={`${styles.navItem} ${
                currentTab === AUTH_SETTINGS_TABS.OIDC && styles.isActive
              }`}
              onClick={() => setCurrentTab(AUTH_SETTINGS_TABS.OIDC)}
            >
              <div className={styles.text}>OIDC Settings</div>
            </li>
          </ul>
        </nav>
      </div>
      <div className={styles.content}>{content}</div>
    </div>
  );
};

export default AuthenticationSettings;
