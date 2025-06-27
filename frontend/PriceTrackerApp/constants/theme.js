// constants/theme.js - MODERNIZED VERSION
const theme = {
  colors: {
    // Primary Brand Colors (New: Indigo)
    primary: {
      50: '#eef2ff',
      100: '#e0e7ff',
      200: '#c7d2fe',
      300: '#a5b4fc',
      400: '#818cf8',
      500: '#6366f1', // Main primary color
      600: '#4f46e5',
      700: '#4338ca',
      900: '#312e81',
    },
    
    // Secondary Colors (New: Violet)
    secondary: {
      50: '#f5f3ff',
      100: '#ede9fe',
      200: '#ddd6fe',
      500: '#8b5cf6', // Main secondary color
      600: '#7c3aed',
    },
    
    // Success/Price Colors (Vibrant Green)
    success: {
      50: '#f0fdf4',
      100: '#dcfce7',
      500: '#22c55e',
      600: '#16a34a',
      700: '#15803d',
    },
    
    // Warning Colors (Amber)
    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      500: '#f59e0b',
      600: '#d97706',
    },
    
    // Error Colors (Vibrant Red)
    error: {
      50: '#fef2f2',
      100: '#fee2e2',
      500: '#ef4444',
      600: '#dc2626',
    },

    // Info Colors (Sky Blue - for the fallback badge)
    info: {
      50: '#f0f9ff',
      100: '#e0f2fe',
      500: '#0ea5e9',
      700: '#0369a1',
    },
    
    // Neutral Colors (Refined Grayscale)
    gray: {
      50: '#f8fafc',  // Slightly off-white
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
    },
    
    // Semantic Colors
    background: '#f8fafc', // Softer background
    surface: '#ffffff',
    text: {
      primary: '#1e293b',   // Dark Slate
      secondary: '#64748b', // Medium Slate
      disabled: '#94a3b8',
      inverse: '#ffffff',
    },
    
    // Gradient Colors (New, vibrant gradients)
    gradients: {
      primary: ['#4f46e5', '#7c3aed'],
      success: ['#16a34a', '#15803d'],
      sunset: ['#f97316', '#ea580c'], // Orange
      ocean: ['#0ea5e9', '#0284c7'], // Sky Blue
    }
  },
  
  typography: {
    fontFamily: {
      regular: 'System', // Keep your original font settings
      medium: 'System',
      bold: 'System',
    },
    fontSize: {
      xs: 12, sm: 14, base: 16, lg: 18, xl: 20,
      '2xl': 24, '3xl': 30, '4xl': 36,
    },
    fontWeight: {
      normal: '400', medium: '500', semibold: '600', bold: '700',
    },
    lineHeight: {
      tight: 1.25, normal: 1.5, relaxed: 1.75,
    }
  },
  
  spacing: {
    xs: 4, sm: 8, md: 16, lg: 24, xl: 32,
    '2xl': 48, '3xl': 64,
  },
  
  borderRadius: {
    none: 0, sm: 4, md: 8, lg: 12, xl: 16, '2xl': 24, full: 9999,
  },
  
  // Subtle, more modern shadows
  shadows: {
    sm: {
      shadowColor: '#0f172a', // Darker slate for better contrast
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 2.22,
      elevation: 2,
    },
    md: {
      shadowColor: '#0f172a',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.1,
      shadowRadius: 4.65,
      elevation: 5,
    },
    lg: {
      shadowColor: '#0f172a',
      shadowOffset: { width: 0, height: 6 },
      shadowOpacity: 0.15,
      shadowRadius: 8.49,
      elevation: 10,
    },
    xl: {
      shadowColor: '#0f172a',
      shadowOffset: { width: 0, height: 10 },
      shadowOpacity: 0.2,
      shadowRadius: 12.35,
      elevation: 16,
    }
  },
  
  animations: {
    duration: {
      fast: 150,
      normal: 200,
      slow: 300,
    },
    easing: {
      in: 'ease-in',
      out: 'ease-out',
      inOut: 'ease-in-out',
    }
  }
};
  
// Utility functions (preserved from your original file)
export const getColor = (colorPath) => {
  const keys = colorPath.split('.');
  let color = theme.colors;
  
  for (const key of keys) {
    if (color && typeof color === 'object' && key in color) {
      color = color[key];
    } else {
      return theme.colors.gray[500]; // Fallback if path is invalid
    }
  }
  
  return color;
};
  
export const createGradientStyle = (gradientName) => ({
  background: `linear-gradient(135deg, ${theme.colors.gradients[gradientName].join(', ')})`,
});
  
export default theme;