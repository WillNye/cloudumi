export const extractErrorMessage = error => {
  let message = '';

  if (typeof error === 'string') {
    message = error;
  } else if (error && typeof error === 'object') {
    if (error.message) {
      message = error.message;
    } else if (error.error) {
      message = error.error;
    } else if (Array.isArray(error)) {
      message = error.map(e => extractErrorMessage(e)).join(', ');
    } else if (error.data) {
      message = extractErrorMessage(error.data);
    }
  }

  return message;
};
