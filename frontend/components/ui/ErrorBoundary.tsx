'use client'
import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallbackTitle?: string
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * ErrorBoundary — Catches unhandled React errors and shows a recovery UI.
 * Prevents the entire app from crashing due to a single component failure.
 * Provides a "Try Again" button for user recovery.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  handleGoHome = () => {
    if (typeof window !== 'undefined') {
      window.location.href = '/'
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#050608',
            color: '#F8FAFC',
            fontFamily: 'Inter, -apple-system, sans-serif',
            padding: 24,
          }}
        >
          <div
            style={{
              maxWidth: 480,
              textAlign: 'center',
              padding: 40,
              borderRadius: 20,
              border: '1px solid rgba(239, 68, 68, 0.2)',
              background: 'linear-gradient(180deg, rgba(239, 68, 68, 0.06) 0%, rgba(10, 10, 11, 0.95) 100%)',
            }}
          >
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 16,
                background: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 28,
                margin: '0 auto 20px',
              }}
            >
              ⚠️
            </div>

            <h2 style={{ fontSize: 18, fontWeight: 700, margin: '0 0 8px' }}>
              {this.props.fallbackTitle || 'Something went wrong'}
            </h2>

            <p style={{ fontSize: 13, color: 'rgba(248,250,252,0.5)', lineHeight: 1.6, margin: '0 0 24px' }}>
              NyayaPramaan encountered an unexpected error. Your data is safe.
              Please try again or return to the homepage.
            </p>

            {this.state.error && (
              <pre
                style={{
                  fontSize: 11,
                  color: 'rgba(248,250,252,0.3)',
                  background: 'rgba(0,0,0,0.4)',
                  padding: '10px 14px',
                  borderRadius: 10,
                  textAlign: 'left',
                  overflow: 'auto',
                  maxHeight: 100,
                  marginBottom: 20,
                  border: '1px solid rgba(255,255,255,0.06)',
                  fontFamily: 'monospace',
                }}
              >
                {this.state.error.message}
              </pre>
            )}

            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button
                onClick={this.handleRetry}
                style={{
                  padding: '10px 20px',
                  borderRadius: 12,
                  background: 'linear-gradient(135deg, #3B82F6, #6366F1)',
                  border: 'none',
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Try Again
              </button>
              <button
                onClick={this.handleGoHome}
                style={{
                  padding: '10px 20px',
                  borderRadius: 12,
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: 'rgba(248,250,252,0.6)',
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
