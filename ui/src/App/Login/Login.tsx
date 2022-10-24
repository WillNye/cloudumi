import { useAuth } from 'core/Auth';
import { FC } from 'react';
import { Helmet } from 'react-helmet-async';
import { useForm } from 'react-hook-form';
import css from './Login.module.css';

export const Login: FC = () => {
  const { login } = useAuth();
  const { register, handleSubmit } = useForm({
    defaultValues: {
      username: '',
      password: ''
    }
  });

  const onSubmit = async data => {
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
          <input type="email" {...register('username')} />
          <br />
          <input type="password" {...register('password')} />
          <br />
          <button type="submit">Login</button>
        </form>
      </div>
    </>
  );
};
