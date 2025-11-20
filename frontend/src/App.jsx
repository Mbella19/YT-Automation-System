import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/Layout'

// Pages
import Welcome from './pages/Welcome'
import Auth from './pages/Auth'
import Decision from './pages/Decision'
import Photos from './pages/Photos'
import Wardrobe from './pages/Wardrobe'
import TryOnStudio from './pages/TryOnStudio'
import SavedLooks from './pages/SavedLooks'
import StyleMyLook from './pages/StyleMyLook'
import StyleDuels from './pages/StyleDuels'

function PrivateRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? (
    <Layout>{children}</Layout>
  ) : (
    <Navigate to="/auth" replace />
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/auth" element={<Auth />} />
        <Route
          path="/decision"
          element={
            <PrivateRoute>
              <Decision />
            </PrivateRoute>
          }
        />
        <Route
          path="/photos"
          element={
            <PrivateRoute>
              <Photos />
            </PrivateRoute>
          }
        />
        <Route
          path="/wardrobe"
          element={
            <PrivateRoute>
              <Wardrobe />
            </PrivateRoute>
          }
        />
        <Route
          path="/tryon"
          element={
            <PrivateRoute>
              <TryOnStudio />
            </PrivateRoute>
          }
        />
        <Route
          path="/saved"
          element={
            <PrivateRoute>
              <SavedLooks />
            </PrivateRoute>
          }
        />
        <Route
          path="/style-me"
          element={
            <PrivateRoute>
              <StyleMyLook />
            </PrivateRoute>
          }
        />
        <Route
          path="/duels"
          element={
            <PrivateRoute>
              <StyleDuels />
            </PrivateRoute>
          }
        />
      </Routes>
    </Router>
  )
}

export default App

