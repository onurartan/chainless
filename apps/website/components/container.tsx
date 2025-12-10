import React, { ReactNode } from "react";
import { cn } from "fumadocs-ui/utils/cn";

interface ContainerProps {
  as?: "div" | "section";
  className?: string;
  children: ReactNode;
  [key: string]: any;
}

const Container: React.FC<ContainerProps> = ({
  as: Component = "section",
  className,
  children,
  ...rest
}) => {
  return (
    <Component
      className={cn("min-h-screen max-w-7xl w-full", className)}
      {...rest}
    >
      {children}
    </Component>
  );
};

export default Container;
