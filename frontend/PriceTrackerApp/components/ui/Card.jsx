// components/ui/Card.jsx
import React from 'react';
import { View, StyleSheet } from 'react-native';
import theme from '../../constants/theme';

const Card = ({ children, style, shadow = 'md', ...props }) => {
  return (
    <View
      style={[
        styles.card,
        theme.shadows[shadow],
        style
      ]}
      {...props}
    >
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.xl,
    padding: theme.spacing.lg,
  },
});

export default Card;