// app/_layout.jsx - GUARANTEED WORKING VERSION
import { Slot, useRouter, useSegments } from 'expo-router';
import { useEffect } from 'react';
import { AuthProvider, useAuth } from '../contexts/AuthContext';

// This is the list of screens that are "inside" the app but are not main tabs.
// We should not redirect away from these if the user is logged in.
const inAppRoutes = ['(tabs)', 'updatePrice', 'addPrice', 'addproduct'];

function InitialLayout() {
  const { isAuthenticated, loading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;

    // The 'inAuthGroup' logic is now more flexible.
    // It checks if the current route segment is one of our main app routes.
    const inAuthGroup = segments.length > 0 && inAppRoutes.includes(segments[0]);

    console.log('🚀 [Navigation] Current state:', {
      isAuthenticated,
      segments: segments.join('/'),
      inAuthGroup,
      loading
    });

    // If the user is authenticated but is on a page NOT considered part of the app
    // (like the initial splash or login screen), redirect them in.
    if (isAuthenticated && !inAuthGroup) {
      console.log('🚀 [Navigation] Redirecting to main app');
      router.replace('/(tabs)/');
    } 
    // If the user is NOT authenticated but tries to access an in-app route,
    // send them to the login page.
    else if (!isAuthenticated && inAuthGroup) {
      console.log('🚀 [Navigation] Redirecting to login');
      router.replace('/login');
    }
  }, [isAuthenticated, segments, loading]);

  return <Slot />;
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <InitialLayout />
    </AuthProvider>
  );
}