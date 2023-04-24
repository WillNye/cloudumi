import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Breadcrumbs } from '../Breadcrumbs';

const testItems = [
  { name: 'Home', url: '/' },
  { name: 'Page 1', url: '/page1' },
  { name: 'Page 2', url: '/page2' }
];

describe('Test Breadcrumbs', () => {
  test('renders breadcrumbs correctly and sets active class to last breadcrumb', () => {
    render(
      <MemoryRouter>
        <Breadcrumbs items={testItems} />
      </MemoryRouter>
    );

    testItems.forEach((item, index) => {
      const linkElement = screen.getByText(item.name);
      expect(linkElement).toBeInTheDocument();
      expect(linkElement).toHaveAttribute('href', item.url);

      const isLastElement = index === testItems.length - 1;
      if (isLastElement) {
        expect(linkElement).toHaveClass('active');
      }
    });
  });
});
