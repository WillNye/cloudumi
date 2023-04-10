import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/react';
import { App } from './App';
import { BrowserRouter } from 'react-router-dom';

describe('<App />', () => {
  test('App renders properly', () => {
    const wrapper = render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(wrapper).toBeDefined();
    expect(wrapper).not.toBeNull();
  });
});
