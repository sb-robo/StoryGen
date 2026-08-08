import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { JobsProvider } from './context/JobsContext'
import { GuestRoute, ProtectedRoute } from './auth/ProtectedRoute'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Layout } from './components/Layout'
import { BrdDetailPage } from './pages/BrdDetailPage'
import { BrdListPage } from './pages/BrdListPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary
        title="StoryGen hit an unexpected error"
        fallbackAction={
          <a href="/" className="btn btn-secondary">
            Reload app
          </a>
        }
      >
        <AuthProvider>
          <JobsProvider>
            <Routes>
              <Route
                path="/login"
                element={
                  <GuestRoute>
                    <LoginPage />
                  </GuestRoute>
                }
              />
              <Route
                path="/register"
                element={
                  <GuestRoute>
                    <RegisterPage />
                  </GuestRoute>
                }
              />
              <Route
                path="/forgot-password"
                element={
                  <GuestRoute>
                    <ForgotPasswordPage />
                  </GuestRoute>
                }
              />
              <Route
                path="/reset-password"
                element={
                  <GuestRoute>
                    <ResetPasswordPage />
                  </GuestRoute>
                }
              />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <ErrorBoundary title="Could not load BRD list">
                        <BrdListPage />
                      </ErrorBoundary>
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/brds/:id"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <ErrorBoundary
                        title="Could not load this BRD"
                        fallbackAction={
                          <Link to="/" className="btn btn-secondary">
                            Back to BRDs
                          </Link>
                        }
                      >
                        <BrdDetailPage />
                      </ErrorBoundary>
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </JobsProvider>
        </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  )
}
