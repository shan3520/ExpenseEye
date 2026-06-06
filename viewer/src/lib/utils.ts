import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a number as INR with Indian digit grouping (e.g. ₹1,23,456).
 * Pin the locale so figures read identically regardless of the user's machine.
 * Whole rupees by default; pass `decimals` for paise.
 */
export function inr(n: number, decimals = 0) {
  return (
    '₹' +
    n.toLocaleString('en-IN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })
  )
}
