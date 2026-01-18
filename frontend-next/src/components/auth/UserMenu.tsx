'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { User, LogOut, Settings, CreditCard } from 'lucide-react';

export function UserMenu() {
  const router = useRouter();
  const { user, logout } = useAuth();

  if (!user) return null;

  // Get initials for avatar
  const getInitials = () => {
    if (user.full_name) {
      return user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    return user.email[0].toUpperCase();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.full_name || user.email}
              className="w-6 h-6 rounded-full"
            />
          ) : (
            <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
              {getInitials()}
            </div>
          )}
          <span className="hidden md:inline text-sm truncate max-w-[150px]">
            {user.full_name || user.email}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col">
            <span className="font-medium">{user.full_name || 'User'}</span>
            <span className="text-xs text-muted-foreground truncate">
              {user.email}
            </span>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push('/settings')}>
          <User className="w-4 h-4 mr-2" />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem disabled>
          <CreditCard className="w-4 h-4 mr-2" />
          <div className="flex flex-col">
            <span>Usage</span>
            <span className="text-xs text-muted-foreground">
              {user.total_workflows} workflows / ${user.total_cost.toFixed(2)}
            </span>
          </div>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings')}>
          <Settings className="w-4 h-4 mr-2" />
          Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout} className="text-destructive">
          <LogOut className="w-4 h-4 mr-2" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
