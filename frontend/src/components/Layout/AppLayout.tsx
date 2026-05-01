import type { ReactNode } from "react";

interface AppLayoutProps {
  header: ReactNode;
  sidebar?: ReactNode;
  map: ReactNode;
  detail?: ReactNode;
  mobileDrawer?: ReactNode;
}

export function AppLayout({ header, sidebar, map, detail, mobileDrawer }: AppLayoutProps) {
  return (
    <div className="h-full flex flex-col">
      {header}
      <div className="flex-1 flex relative overflow-hidden">
        {sidebar && (
          <aside className="hidden md:block w-80 border-r overflow-y-auto bg-white z-10">
            {sidebar}
          </aside>
        )}
        <div className="flex-1">{map}</div>
        {detail}
        {mobileDrawer}
      </div>
    </div>
  );
}
