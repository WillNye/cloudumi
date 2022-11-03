import { useAuth } from 'core/Auth';
import { FC } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import css from './Credentials.module.css';
import { Navigate } from 'react-router-dom';

const credentialsSchema = Yup.object().shape({
  username: Yup.string().email('Invalid email').required('Required'),
  password: Yup.string().required('Required')
});

export const Credentials: FC = () => {
  const { login, user } = useAuth();

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

  if (user) {
    return <Navigate to="/" />;
  }

  return (
    <>
      <Helmet>
        <title>Login</title>
      </Helmet>
      <div className={css.container}>
        <h1>Login</h1>
        <form onSubmit={handleSubmit(onSubmit)}>
          <input autoFocus type="email" {...register('username')} />
          <br />
          <input
            type="password"
            autoCapitalize="none"
            autoCorrect="off"
            {...register('password')}
          />
          <br />
          <button type="submit" disabled={isSubmitting || !isValid}>
            {isSubmitting ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </>
  );
};
