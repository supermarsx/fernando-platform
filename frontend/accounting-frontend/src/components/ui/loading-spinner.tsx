import * as React from "react";

export interface LoadingSpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md" | "lg" | "xl";
  variant?: "primary" | "secondary" | "white";
}

const LoadingSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ className = "", size = "md", variant = "primary", ...props }, ref) => {
    const sizes = {
      sm: "h-4 w-4",
      md: "h-8 w-8",
      lg: "h-12 w-12",
      xl: "h-16 w-16",
    };

    const variants = {
      primary: "border-primary border-t-primary",
      secondary: "border-secondary border-t-secondary",
      white: "border-white border-t-white",
    };

    return (
      <div
        ref={ref}
        className={`animate-spin rounded-full border-2 border-transparent ${sizes[size]} ${variants[variant]} ${className}`}
        {...props}
      />
    );
  }
);
LoadingSpinner.displayName = "LoadingSpinner";

export { LoadingSpinner };