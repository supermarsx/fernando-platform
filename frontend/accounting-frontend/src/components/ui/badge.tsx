import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "error" | "primary";
}

function Badge({ className = "", variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-primary text-primary-foreground hover:bg-primary/80",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/80",
    outline: "border border-border bg-background/80 text-foreground",
    success: "bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 hover:bg-success-200 dark:hover:bg-success-800/40",
    warning: "bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 hover:bg-warning-200 dark:hover:bg-warning-800/40",
    error: "bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300 hover:bg-error-200 dark:hover:bg-error-800/40",
    primary: "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-800/40",
  };

  return (
    <div
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 hover:scale-105 ${variants[variant]} ${className}`}
      {...props}
    />
  );
}

export { Badge };
