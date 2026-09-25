'use client'
import { ErrorBoundary } from './ErrorBoundary'

/**
 * Client-side wrapper for ErrorBoundary.
 * Required because ErrorBoundary is a class component and the root layout is a server component.
 */
export function ErrorBoundaryWrapper({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary fallbackTitle="NyayaPramaan encountered an error">
      {children}
    </ErrorBoundary>
  )
}
