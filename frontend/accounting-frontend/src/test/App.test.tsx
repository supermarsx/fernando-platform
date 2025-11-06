import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App from '../App'

// Mock the components that might have external dependencies
vi.mock('../components/LoadingSpinner', () => ({
  default: () => <div data-testid="loading-spinner">Loading...</div>,
}))

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('App Component', () => {
  it('renders without crashing', () => {
    renderWithRouter(<App />)
    expect(document.body).toBeInTheDocument()
  })

  it('displays the main application', () => {
    renderWithRouter(<App />)
    // This is a basic test - adjust based on your actual app structure
    expect(screen.getByText(/welcome/i)).toBeInTheDocument()
  })

  it('handles navigation properly', () => {
    renderWithRouter(<App />)
    const navElement = screen.getByRole('navigation')
    expect(navElement).toBeInTheDocument()
  })

  it('applies proper CSS classes', () => {
    renderWithRouter(<App />)
    const appElement = document.querySelector('.app')
    expect(appElement).toBeInTheDocument()
  })
})