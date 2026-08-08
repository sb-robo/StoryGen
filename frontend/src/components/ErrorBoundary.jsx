import { Component } from 'react'

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('UI error boundary caught:', error, info)
  }

  handleRetry = () => {
    this.setState({ error: null })
    this.props.onReset?.()
  }

  render() {
    if (this.state.error) {
      const title = this.props.title || 'Something went wrong'
      const message =
        this.props.message ||
        this.state.error?.message ||
        'This section failed to render. Try again or go back.'

      return (
        <div className="error-boundary panel" role="alert">
          <h2>{title}</h2>
          <p className="form-error">{message}</p>
          <div className="error-boundary-actions">
            <button type="button" className="btn btn-primary" onClick={this.handleRetry}>
              Try again
            </button>
            {this.props.fallbackAction}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
