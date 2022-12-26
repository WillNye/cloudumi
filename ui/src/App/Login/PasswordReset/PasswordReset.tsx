import React, { useState } from 'react';
import { Auth } from 'aws-amplify';

export function PasswordReset() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordConfirmation, setPasswordConfirmation] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);
  const [error, setError] = useState(null);
  const token = new URLSearchParams(window.location.search).get('token');

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      if (!token) {
        // TODO (Kayizzi): Make a POST REQUEST with user's e-mail to /api/v4/users/forgot_password, it's in
        // queries.ts under `USER_SEND_RESET_PASSWORD_LINK`.
        // BODY contents:
        // {
        //   "command": "request",
        //   "email": "curtis@noq.dev"
        // }
      } else {
        // TODO (Kayizzi): Make a POST REQUEST to /api/v4/users/forgot_password, body content:
      }
    } catch (error) {
      setError(error);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {error && <p>{error.message}</p>}
      {!token && (
        <>
          <label>
            Email:
            <input
              type="email"
              value={email}
              onChange={event => setEmail(event.target.value)}
            />
          </label>
          <button type="submit">Send Password Reset link</button>
        </>
      )}
      {token && (
        <>
          <label>
            New Password:
            <input
              type="password"
              value={newPassword}
              onChange={event => setNewPassword(event.target.value)}
            />
          </label>
          {/* TODO (Kayizzi): Add a password strength meter here. */}
          <label>
            Verify New Password:
            <input
              type="password"
              value={passwordConfirmation}
              onChange={event => setPasswordConfirmation(event.target.value)}
            />
          </label>
          <button type="submit">Reset Password</button>
        </>
      )}
      {/* TODO (Kayizzi): We should link the user to the login page here.  */}
      {resetSuccess && (
        <p>
          Your password has been successfully reset. You can now log in with
          your new password.
        </p>
      )}
    </form>
  );
}
