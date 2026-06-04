import { PiSpinnerGap } from "react-icons/pi";

export function Spinner({ className = "" }: { className?: string }) {
  return <PiSpinnerGap className={`animate-spin text-brand ${className}`} />;
}
