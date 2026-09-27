"use client";

import * as React from "react";
import { Menu } from "lucide-react";

import { SidebarContent } from "@/components/layout/sidebar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

export function MobileNav() {
  const [open, setOpen] = React.useState(false);

  return (
    <>
      <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setOpen(true)}
              aria-label="Open navigation">
        <Menu className="h-5 w-5" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          className="left-0 top-0 h-full max-w-[264px] translate-x-0 translate-y-0 rounded-none border-r p-0"
          aria-describedby={undefined}
        >
          <DialogTitle className="sr-only">Navigation</DialogTitle>
          <SidebarContent onNavigate={() => setOpen(false)} />
        </DialogContent>
      </Dialog>
    </>
  );
}
