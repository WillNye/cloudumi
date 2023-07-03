export const extractErrorMessage = error => {
  if (typeof error === 'string') {
    return error;
  } else if (error && typeof error === 'object') {
    if (error.message) {
      return error.message;
    } else if (error.error) {
      return error.error;
    } else if (Array.isArray(error)) {
      return error.map(e => extractErrorMessage(e)).join(', ');
    } else if (error.data) {
      return extractErrorMessage(error.data);
    } else if (error.errors) {
      return extractErrorMessage(error.errors);
    }
  }
  return '';
};
