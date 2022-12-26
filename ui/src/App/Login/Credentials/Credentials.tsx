import { useAuth } from 'core/Auth';
import { FC } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { Link } from 'react-router-dom';
import { yupResolver } from '@hookform/resolvers/yup';
import css from './Credentials.module.css';
import { Navigate } from 'react-router-dom';
import { MotionGroup, MotionItem } from 'reablocks';
import { ReactComponent as Logo } from 'assets/brand/logo-bw.svg';

const credentialsSchema = Yup.object().shape({
  username: Yup.string().email('Invalid email').required('Required'),
  password: Yup.string().required('Required')
});

export const Credentials: FC = () => {
  const { login, user, ssoLogin } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, isValid }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(credentialsSchema),
    defaultValues: {
      username: '',
      password: ''
    }
  });

  const onSubmit = async data => {
    // TODO: In this `login` method here, we should detect
    // if the login needs 2fa, change password, etc and then
    // navigate the user to that route. This should NOT be in
    // this component since its a global concern.
    await login(data);
  };

  const onSubmitSSOSignIn = async () => {
    console.log('here');
    await ssoLogin();
  };

  if (user) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Login</title>
      </Helmet>
      <MotionGroup className={css.container}>
        {/* TODO (@kayizzi)) Need Noq favicon. This exists in current `frontend` */}
        {/* TODO (@kayizzi)) Use larget box, per Figma */}
        <MotionItem className={css.box}>
          <Logo />
          <br />
          <form onSubmit={handleSubmit(onSubmit)}>
            {/* TODO (@kayizzi)) Add e-mail and password labels per Figma */}

            {/* TODO (@kayizzi)) We cannot assume the username is an e-mail. */}
            {/* Please remove regex requirement for email */}
            <input autoFocus type="email" {...register('username')} />
            <Link to={'password-reset'}>Forgot your password?</Link>
            <br />
            <br />
            <input
              type="password"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('password')}
            />
            <br />
            <br />
            {/* TODO (@kayizzi)) switch to styled button */}
            <button type="submit" disabled={isSubmitting || !isValid}>
              {isSubmitting ? 'Logging in...' : 'Login'}
            </button>
            <br />
            <br />
            {/* TODO (@kayizzi)) We must give the user an indication when sign-in has failed and why it has failed (Invalid password or invalid mfa?)  */}

            {/* TODO (@kayizzi)) Add a `Sign in with your Identity Provider` button. I added it to Figma */}
          </form>
          <button onClick={onSubmitSSOSignIn} value="sso_provider">
            {isSubmitting
              ? 'Logging in...'
              : 'Sign in with your Identity Provider'}
          </button>
        </MotionItem>
      </MotionGroup>
    </>
  );
};
