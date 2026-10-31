import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// shadcn-style variant boundary, adapted to the existing Vite workstation.
const variants = cva(
  "wb-button inline-flex items-center justify-center gap-2",
  {
    variants: {
      variant: { default: "wb-button-default", ghost: "wb-button-ghost" },
    },
    defaultVariants: { variant: "default" },
  },
);
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof variants>
>(({ className, variant, type = "button", ...props }, ref) => (
  <button
    ref={ref}
    type={type}
    className={twMerge(clsx(variants({ variant }), className))}
    {...props}
  />
));
Button.displayName = "Button";
