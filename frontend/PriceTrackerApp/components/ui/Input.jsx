// components/ui/Input.jsx
import React, { forwardRef, useState } from 'react';
import { 
  View, 
  TextInput, 
  Text, 
  StyleSheet, 
  TouchableOpacity 
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import theme from '../../constants/theme';

const Input = forwardRef(({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  onRightIconPress,
  style,
  multiline = false,
  secureTextEntry = false,
  ...props
}, ref) => {
  const [isFocused, setIsFocused] = useState(false);
  const [isSecure, setIsSecure] = useState(secureTextEntry);

  const inputStyles = [
    styles.input,
    isFocused && styles.inputFocused,
    error && styles.inputError,
    leftIcon && styles.inputWithLeftIcon,
    (rightIcon || secureTextEntry) && styles.inputWithRightIcon,
    multiline && styles.inputMultiline,
    style
  ];

  return (
    <View style={styles.container}>
      {label && <Text style={styles.label}>{label}</Text>}
      
      <View style={styles.inputContainer}>
        {leftIcon && (
          <View style={styles.leftIconContainer}>
            <Ionicons
              name={leftIcon}
              size={20}
              color={isFocused ? theme.colors.primary[500] : theme.colors.gray[400]}
            />
          </View>
        )}
        
        <TextInput
          ref={ref}
          style={inputStyles}
          placeholderTextColor={theme.colors.gray[400]}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          secureTextEntry={isSecure}
          multiline={multiline}
          textAlignVertical={multiline ? 'top' : 'center'}
          {...props}
        />
        
        {(rightIcon || secureTextEntry) && (
          <TouchableOpacity
            style={styles.rightIconContainer}
            onPress={secureTextEntry ? () => setIsSecure(!isSecure) : onRightIconPress}
          >
            <Ionicons
              name={secureTextEntry ? (isSecure ? 'eye-off' : 'eye') : rightIcon}
              size={20}
              color={theme.colors.gray[400]}
            />
          </TouchableOpacity>
        )}
      </View>
      
      {error && <Text style={styles.error}>{error}</Text>}
      {hint && !error && <Text style={styles.hint}>{hint}</Text>}
    </View>
  );
});

const styles = StyleSheet.create({
  container: {
    marginBottom: theme.spacing.md,
  },
  label: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: theme.typography.fontWeight.medium,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  inputContainer: {
    position: 'relative',
    flexDirection: 'row',
    alignItems: 'center',
  },
  input: {
    flex: 1,
    backgroundColor: theme.colors.gray[50],
    borderWidth: 1,
    borderColor: theme.colors.gray[200],
    borderRadius: theme.borderRadius.lg,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text.primary,
  },
  inputFocused: {
    borderColor: theme.colors.primary[500],
    backgroundColor: theme.colors.surface,
  },
  inputError: {
    borderColor: theme.colors.error[500],
  },
  inputWithLeftIcon: {
    paddingLeft: theme.spacing.xl + theme.spacing.md,
  },
  inputWithRightIcon: {
    paddingRight: theme.spacing.xl + theme.spacing.md,
  },
  inputMultiline: {
    height: 100,
    textAlignVertical: 'top',
  },
  leftIconContainer: {
    position: 'absolute',
    left: theme.spacing.md,
    zIndex: 1,
  },
  rightIconContainer: {
    position: 'absolute',
    right: theme.spacing.md,
    zIndex: 1,
  },
  error: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.error[500],
    marginTop: theme.spacing.xs,
  },
  hint: {
    fontSize: theme.typography.fontSize.xs,
    color: theme.colors.gray[500],
    marginTop: theme.spacing.xs,
  },
});

export default Input;