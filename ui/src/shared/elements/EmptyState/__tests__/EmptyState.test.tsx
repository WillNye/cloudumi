import { render, screen } from '@testing-library/react';
import { EmptyState } from '../EmptyState';

describe('Empty State', () => {
  test('renders the empty state component with correct elements', () => {
    render(<EmptyState />);

    const imgElement = screen.getByRole('img');
    expect(imgElement).toBeInTheDocument();

    const noResultFoundElement = screen.getByText('No result found!');
    expect(noResultFoundElement).toBeInTheDocument();

    const noResultsTextElement = screen.getByText(
      'No results found that match the above query'
    );
    expect(noResultsTextElement).toBeInTheDocument();
  });
});
