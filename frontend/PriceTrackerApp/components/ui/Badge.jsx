// components/ui/Badge.jsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import theme from '../../constants/theme';

const Badge = ({ 
  children, 
  variant = 'primary', 
  size = 'medium',
  style 
}) => {
  const badgeStyles = [
    styles.badge,
    styles[variant],
    styles[size],
    style
  ];

  const textStyles = [
    styles.text,
    styles[`${variant}Text`],
    styles[`${size}Text`]
  ];

  return (
    <View style={badgeStyles}>
      <Text style={textStyles}>{children}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    borderRadius: theme.borderRadius.full,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    alignSelf: 'flex-start',
  },
  
  // Variants
  primary: {
    backgroundColor: theme.colors.primary[100],
  },
  success: {
    backgroundColor: theme.colors.success[100],
  },
  warning: {
    backgroundColor: theme.colors.warning[100],
  },
  error: {
    backgroundColor: theme.colors.error[100],
  },
  gray: {
    backgroundColor: theme.colors.gray[100],
  },
  
  // Sizes
  small: {
    paddingHorizontal: theme.spacing.xs,
    paddingVertical: 2,
  },
  medium: {
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
  },
  large: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
  },
  
  // Text styles
  text: {
    fontWeight: theme.typography.fontWeight.medium,
    textAlign: 'center',
  },
  primaryText: {
    color: theme.colors.primary[700],
  },
  successText: {
    color: theme.colors.success[700],
  },
  warningText: {
    color: theme.colors.warning[700],
  },
  errorText: {
    color: theme.colors.error[700],
  },
  grayText: {
    color: theme.colors.gray[700],
  },
  
  // Size text
  smallText: {
    fontSize: theme.typography.fontSize.xs,
  },
  mediumText: {
    fontSize: theme.typography.fontSize.sm,
  },
  largeText: {
    fontSize: theme.typography.fontSize.base,
  },
});

export default Badge;