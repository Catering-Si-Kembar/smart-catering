'use client';

import * as React from 'react';
import AutorenewRoundedIcon from '@mui/icons-material/AutorenewRounded';
import CheckCircleOutlineRoundedIcon from '@mui/icons-material/CheckCircleOutlineRounded';
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import WarningAmberRoundedIcon from '@mui/icons-material/WarningAmberRounded';
import type { SvgIconProps } from '@mui/material/SvgIcon';
import { cn } from '@/lib/utils';

export type StatusTone = 'info' | 'success' | 'warning' | 'error' | 'loading';

export interface StatusBannerProps {
  readonly tone?: StatusTone;
  readonly title: string;
  readonly detail?: string;
  readonly actionLabel?: string;
  readonly onAction?: () => void;
  readonly className?: string;
}

const TONE_CONFIG: Record<
  StatusTone,
  {
    readonly icon: React.ComponentType<SvgIconProps>;
    readonly containerClass: string;
    readonly iconClass: string;
    readonly titleClass: string;
    readonly textClass: string;
  }
> = {
  info: {
    icon: InfoOutlinedIcon,
    containerClass: 'bg-blue-50 border-blue-300 text-blue-950',
    iconClass: 'text-blue-700',
    titleClass: 'text-blue-950',
    textClass: 'text-blue-900',
  },
  loading: {
    icon: AutorenewRoundedIcon,
    containerClass: 'bg-slate-50 border-slate-300 text-slate-950',
    iconClass: 'text-[#21201c] animate-spin',
    titleClass: 'text-slate-950',
    textClass: 'text-slate-800',
  },
  success: {
    icon: CheckCircleOutlineRoundedIcon,
    containerClass: 'bg-[#ecfdf5] border-[#166534]/30 text-[#166534]',
    iconClass: 'text-[#166534]',
    titleClass: 'text-[#166534]',
    textClass: 'text-[#14532d]',
  },
  warning: {
    icon: WarningAmberRoundedIcon,
    containerClass: 'bg-amber-50 border-amber-300 text-amber-950',
    iconClass: 'text-amber-700',
    titleClass: 'text-amber-950',
    textClass: 'text-amber-900',
  },
  error: {
    icon: ErrorOutlineRoundedIcon,
    containerClass: 'bg-rose-50 border-rose-300 text-rose-950',
    iconClass: 'text-rose-700',
    titleClass: 'text-rose-950',
    textClass: 'text-rose-900',
  },
};

export function StatusBanner({
  tone = 'info',
  title,
  detail,
  actionLabel,
  onAction,
  className,
}: StatusBannerProps) {
  const config = TONE_CONFIG[tone];
  const Icon = config.icon;

  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      aria-live="polite"
      className={cn(
        'flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between',
        config.containerClass,
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <Icon
          sx={{ fontSize: 20 }}
          className={cn('mt-0.5 shrink-0', config.iconClass)}
          aria-hidden={true}
        />
        <div className="space-y-0.5">
          <p className={cn('text-sm font-bold leading-snug', config.titleClass)}>{title}</p>
          {detail ? (
            <p className={cn('text-sm leading-relaxed', config.textClass)}>{detail}</p>
          ) : null}
        </div>
      </div>
      {actionLabel && onAction ? (
        <button
          type="button"
          onClick={onAction}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md border border-current px-3 py-2 text-sm font-semibold transition hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current"
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
