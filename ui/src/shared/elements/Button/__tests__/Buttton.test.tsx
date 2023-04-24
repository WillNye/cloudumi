import { render, fireEvent } from '@testing-library/react';
import { Button } from '../Button';
import { BrowserRouter } from 'react-router-dom';

const navigateMock = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => navigateMock
}));

describe('Button', () => {
  it('renders a button with the correct classnames and text', () => {
    const { getByRole, getByText } = render(
      <BrowserRouter>
        <Button>Click me</Button>
      </BrowserRouter>
    );
    const button = getByRole('button');
    expect(button).toHaveClass('btn');
    expect(button).toHaveTextContent('Click me');
  });

  it('triggers onClick when the button is clicked', () => {
    const handleClick = jest.fn();
    const { getByRole } = render(
      <BrowserRouter>
        <Button onClick={handleClick}>Click me</Button>
      </BrowserRouter>
    );
    const button = getByRole('button');
    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalled();
  });

  it('disables the button when disabled prop is passed', () => {
    const { getByRole } = render(
      <BrowserRouter>
        <Button disabled>Click me</Button>
      </BrowserRouter>
    );
    const button = getByRole('button');
    expect(button).toBeDisabled();
  });

  it('navigates to the provided href when asAnchor prop is passed and button is clicked', () => {
    const { getByRole } = render(
      <BrowserRouter>
        <Button asAnchor href="/some-page">
          Click me
        </Button>
      </BrowserRouter>
    );
    const button = getByRole('button');
    fireEvent.click(button);
    expect(navigateMock).toHaveBeenCalledWith('/some-page');
  });
});
