// components/ui/Button.jsx
import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import theme from '../../constants/theme';

const Button = ({
  title,
  onPress,
  variant = 'primary',
  size = 'medium',
  loading = false,
  disabled = false,
  icon,
  style,
  ...props
}) => {
  const buttonStyles = [
    styles.base,
    styles[variant],
    styles[size],
    disabled && styles.disabled,
    style
  ];

  const textStyles = [
    styles.text,
    styles[`${variant}Text`],
    styles[`${size}Text`],
    disabled && styles.disabledText
  ];

  const isGradient = variant === 'primary' || variant === 'success';

  const ButtonContent = () => (
    <>
      {loading ? (
        <ActivityIndicator 
          color={variant === 'outline' ? theme.colors.primary[500] : theme.colors.text.inverse} 
          size="small" 
        />
      ) : (
        <>
          {icon}
          <Text style={textStyles}>{title}</Text>
        </>
      )}
    </>
  );

  if (isGradient && !disabled) {
    return (
      <TouchableOpacity onPress={onPress} disabled={disabled || loading} {...props}>
        <LinearGradient
          colors={theme.colors.gradients[variant === 'success' ? 'success' : 'primary']}
          style={[styles.base, styles[size], style]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
        >
          <ButtonContent />
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      style={buttonStyles}
      onPress={onPress}
      disabled={disabled || loading}
      {...props}
    >
      <ButtonContent />
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: theme.borderRadius.lg,
    ...theme.shadows.sm,
  },
  
  // Variants
  primary: {
    backgroundColor: theme.colors.primary[500],
  },
  secondary: {
    backgroundColor: theme.colors.secondary[500],
  },
  success: {
    backgroundColor: theme.colors.success[500],
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: theme.colors.primary[500],
  },
  ghost: {
    backgroundColor: 'transparent',
  },
  
  // Sizes
  small: {
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
  },
  medium: {
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
  },
  large: {
    paddingVertical: theme.spacing.lg,
    paddingHorizontal: theme.spacing.xl,
  },
  
  // Text styles
  text: {
    fontWeight: theme.typography.fontWeight.semibold,
    textAlign: 'center',
  },
  primaryText: {
    color: theme.colors.text.inverse,
    fontSize: theme.typography.fontSize.base,
  },
  secondaryText: {
    color: theme.colors.text.inverse,
    fontSize: theme.typography.fontSize.base,
  },
  successText: {
    color: theme.colors.text.inverse,
    fontSize: theme.typography.fontSize.base,
  },
  outlineText: {
    color: theme.colors.primary[500],
    fontSize: theme.typography.fontSize.base,
  },
  ghostText: {
    color: theme.colors.primary[500],
    fontSize: theme.typography.fontSize.base,
  },
  
  // Size text
  smallText: {
    fontSize: theme.typography.fontSize.sm,
  },
  mediumText: {
    fontSize: theme.typography.fontSize.base,
  },
  largeText: {
    fontSize: theme.typography.fontSize.lg,
  },
  
  // States
  disabled: {
    backgroundColor: theme.colors.gray[300],
    opacity: 0.6,
  },
  disabledText: {
    color: theme.colors.text.disabled,
  },
});

export default Button;