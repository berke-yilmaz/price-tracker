// types/expo-router.d.ts
declare module 'expo-router' {
    export * from 'expo-router/types';
    
    import React from 'react';
    
    // Stack component ekleyin
    export const Stack: React.ComponentType<{
      screenOptions?: any;
      children?: React.ReactNode;
    }> & {
      Screen: React.ComponentType<{
        name: string;
        component?: React.ComponentType<any>;
        options?: any;
      }>;
    };
    
    // useRouter function
    export function useRouter(): {
      push: (path: string | { pathname: string; params?: any }) => void;
      replace: (path: string | { pathname: string; params?: any }) => void;
      back: () => void;
      canGoBack: () => boolean;
    };
    
    // useLocalSearchParams function
    export function useLocalSearchParams(): Record<string, string | string[]>;
  }