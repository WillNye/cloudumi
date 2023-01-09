import { useAuth } from 'core/Auth';
import { FC, useCallback, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { Link } from 'react-router-dom';
import { yupResolver } from '@hookform/resolvers/yup';
import css from './Credentials.module.css';
import { Navigate } from 'react-router-dom';
import { MotionGroup, MotionItem } from 'reablocks';
import { ReactComponent as Logo } from 'assets/brand/logo-bw.svg';
import { login, signinWithSSO } from 'core/API/auth';
import { Button } from 'shared/elements/Button';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';

const credentialsSchema = Yup.object().shape({
  email: Yup.string().required('Required'),
  password: Yup.string().required('Required')
});

export const Credentials: FC = () => {
  const [loginError, setLoginError] = useState<string | null>(null);
  const [ssoError, setSSOError] = useState<string | null>(null);
  const [isGeneratingSSOLink, setIsGeneratingSSOLink] = useState(false);

  const { user, getUser } = useAuth();

  const resetState = useCallback(() => {
    setLoginError(null);
    setSSOError(null);
  }, []);

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, isValid }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(credentialsSchema),
    defaultValues: {
      email: '',
      password: ''
    }
  });

  const onSubmit = useCallback(
    async data => {
      resetState();
      try {
        await login(data);
        await getUser();
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setLoginError(errorMsg || 'An error occurred while logging in');
      }
    },
    [getUser, resetState]
  );

  const handleSSOLoginIn = useCallback(async () => {
    setIsGeneratingSSOLink(true);
    resetState();
    try {
      const res = await signinWithSSO();
      const data = res?.data;
      setIsGeneratingSSOLink(false);
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      }
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setSSOError(errorMsg || 'Unable to login with SSO');
      setIsGeneratingSSOLink(false);
    }
  }, [resetState]);

  if (user) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Login</title>
      </Helmet>
      <MotionGroup className={css.container}>
        <MotionItem className={css.box}>
          <Logo />
          <br />
          <form className={css.form} onSubmit={handleSubmit(onSubmit)}>
            <Block label="Email" disableLabelPadding>
              <Input
                fullWidth
                size="small"
                autoFocus
                placeholder="Enter Email"
                type="email"
                {...register('email')}
              />
            </Block>

            <Block label="Password" disableLabelPadding>
              <Input
                fullWidth
                size="small"
                type="password"
                placeholder="Enter Password"
                autoCapitalize="none"
                autoCorrect="off"
                {...register('password')}
              />
            </Block>
            {loginError && (
              <Notification
                type={NotificationType.ERROR}
                header={loginError}
                showCloseIcon={false}
              />
            )}
            <br />

            <Button fullWidth type="submit" disabled={isSubmitting || !isValid}>
              {isSubmitting ? 'Logging in...' : 'Login'}
            </Button>
          </form>

          <Button fullWidth onClick={handleSSOLoginIn} value="sso_provider">
            {isGeneratingSSOLink
              ? 'Loading ...'
              : 'Sign-In with your Identity Provider'}
          </Button>
          {ssoError && (
            <Notification
              type={NotificationType.ERROR}
              header={ssoError}
              showCloseIcon={false}
            />
          )}
          <br />
          <Link to="password-reset">Forgot your password?</Link>
        </MotionItem>
      </MotionGroup>
    </>
  );
};
