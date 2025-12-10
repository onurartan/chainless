import { DocsLayout } from 'fumadocs-ui/layouts/notebook';
import type { ReactNode } from "react";
import { baseOptions } from "@/app/layout.config";
import { source } from "@/lib/source";
import Logo from "@/components/logo";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      {...baseOptions}
      nav={{...baseOptions.nav, mode: "auto",title: <Logo iconSize={30}  /> }}
      tree={source.pageTree}
    
    >
      {children}
    </DocsLayout>
  );
}
