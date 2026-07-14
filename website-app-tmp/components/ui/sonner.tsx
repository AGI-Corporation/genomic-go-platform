"use client";

import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react";
import { useTheme } from "next-themes";
import { Toaster as Sonner, type ToasterProps } from "sonner";

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="icon-16" />,
        info: <InfoIcon className="icon-16" />,
        warning: <TriangleAlertIcon className="icon-16" />,
        error: <OctagonXIcon className="icon-16" />,
        loading: <Loader2Icon className="icon-16 animate-spin" />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
          "--action-button-bg": "var(--primary)",
          "--action-button-text": "var(--primary-foreground)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
