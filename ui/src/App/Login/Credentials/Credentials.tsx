import { useAuth } from 'core/Auth';
import { FC, useCallback } from 'react';
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

const credentialsSchema = Yup.object().shape({
  email: Yup.string().email('Invalid email').required('Required'),
  password: Yup.string().required('Required')
});

export const Credentials: FC = () => {
  const { user, getUser } = useAuth();

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
      // TODO: In this `login` method here, we should detect
      // if the login needs 2fa, change password, etc and then
      // navigate the user to that route. This should NOT be in
      // this component since its a global concern.
      try {
        await login(data);
        await getUser();
      } catch (error) {
        // handle login errors
      }
    },
    [getUser]
  );

  const handleSSOLoginIn = useCallback(async () => {
    const res = await signinWithSSO();
    const data = res?.data;
    if (data.redirect_url) {
      window.location.href = data.redirect_url;
    }
  }, []);

  if (user) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Login</title>
      </Helmet>
      <MotionGroup className={css.container}>
        {/* TODO (@kayizzi)) Use larget box, per Figma */}
        <MotionItem className={css.box}>
          <Logo />
          <br />
          <form className={css.form} onSubmit={handleSubmit(onSubmit)}>
            {/* TODO (@kayizzi)) We cannot assume the username is an e-mail. */}
            {/* Please remove regex requirement for email */}
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
            <br />

            <Button fullWidth type="submit" disabled={isSubmitting || !isValid}>
              {isSubmitting ? 'Logging in...' : 'Login'}
            </Button>
            {/* TODO (@kayizzi)) We must give the user an indication when sign-in has failed and why it has failed (Invalid password or invalid mfa?)  */}

            {/* TODO (@kayizzi)) Add a `Sign in with your Identity Provider` button. I added it to Figma here: https://www.figma.com/file/u8pwOpItLV7J1H38Nh92Da/NOQ-App-Design?node-id=289%3A346&t=l5gEJ592lF2gH077-0*/}
          </form>
          <Button fullWidth onClick={handleSSOLoginIn} value="sso_provider">
            {isSubmitting
              ? 'Logging in...'
              : 'Sign-In with your Identity Provider'}
          </Button>
          <br />
          <Link to="password-reset">Forgot your password?</Link>
        </MotionItem>
      </MotionGroup>
    </>
  );
};
