import { useAuth } from 'core/Auth';
import { FC } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import css from './Credentials.module.css';

export const Credentials: FC = () => {
  const { login } = useAuth();
  const { register, handleSubmit, formState: { isSubmitting, isValid } } = useForm({
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
          <input type="password" {...register('password')} />
          <br />
          <button type="submit" disabled={isSubmitting || !isValid}>
            {isSubmitting ? 'Logging in...' : 'Login'}
          </button>
        </form>
      </div>
    </>
  );
};
