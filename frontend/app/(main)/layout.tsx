"use client";

import { SidebarProvider } from "@/contexts/SidebarContext";
import { SidebarLayout } from "@/components/SidebarLayout";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SidebarProvider>
      <SidebarLayout>{children}</SidebarLayout>
    </SidebarProvider>
  );
}
