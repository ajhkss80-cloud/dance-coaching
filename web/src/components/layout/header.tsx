"use client";

import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useQuery } from "@tanstack/react-query";
import { Sun, Moon, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { useState } from "react";
import Link from "next/link";
import { Home, Wand2, Target, Clock, Settings } from "lucide-react";

const titles: Record<string, string> = {
  "/": "대시보드",
  "/generate": "댄스 영상 생성",
  "/coach": "댄스 코칭",
  "/history": "작업 기록",
  "/settings": "설정",
};

const mobileNavItems = [
  { href: "/", label: "홈", icon: Home },
  { href: "/generate", label: "영상 생성", icon: Wand2 },
  { href: "/coach", label: "댄스 코칭", icon: Target },
  { href: "/history", label: "작업 기록", icon: Clock },
  { href: "/settings", label: "설정", icon: Settings },
];

export function Header() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    refetchInterval: 30000,
    retry: false,
  });

  const isHealthy = health?.status === "ok";
  const title = titles[pathname] || "댄스 코칭";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60 lg:px-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="메뉴 열기/닫기"
        >
          <Menu className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-sm" role="status" aria-label="서버 연결 상태">
          <div
            className={cn(
              "h-2.5 w-2.5 rounded-full",
              isHealthy ? "bg-green-500" : "bg-red-500"
            )}
            aria-hidden="true"
          />
          <span className={cn(
            "hidden sm:inline",
            isHealthy ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
          )}>
            {isHealthy ? "서버 연결됨" : "서버 연결 안됨"}
          </span>
        </div>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={`${theme === "dark" ? "라이트" : "다크"} 모드로 전환`}
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
      </div>

      {mobileMenuOpen && (
        <div className="absolute left-0 top-16 w-full border-b border-border bg-background p-4 shadow-lg lg:hidden">
          <nav className="space-y-1">
            {mobileNavItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
}
