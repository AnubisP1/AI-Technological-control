const ICONS = {
  lathe: (
    <>
      <rect x="4" y="26" width="56" height="8" rx="2" />
      <rect x="10" y="18" width="14" height="10" rx="1" />
      <circle cx="46" cy="23" r="9" fill="none" strokeWidth="3" />
      <line x1="24" y1="23" x2="37" y2="23" strokeWidth="3" />
    </>
  ),
  mill: (
    <>
      <rect x="6" y="30" width="52" height="6" rx="2" />
      <rect x="14" y="10" width="8" height="20" rx="1" />
      <rect x="10" y="30" width="16" height="8" rx="1" />
      <line x1="18" y1="10" x2="18" y2="2" strokeWidth="3" />
      <rect x="34" y="20" width="18" height="10" rx="1" fill="none" strokeWidth="2" />
    </>
  ),
  drill: (
    <>
      <rect x="10" y="34" width="44" height="6" rx="2" />
      <rect x="28" y="6" width="8" height="20" rx="1" />
      <polygon points="28,26 36,26 32,34" />
      <line x1="32" y1="6" x2="32" y2="2" strokeWidth="3" />
    </>
  ),
  grind: (
    <>
      <rect x="6" y="28" width="52" height="6" rx="2" />
      <circle cx="32" cy="18" r="10" fill="none" strokeWidth="3" />
      <line x1="32" y1="8" x2="32" y2="2" strokeWidth="3" />
    </>
  ),
  control: (
    <>
      <rect x="14" y="8" width="36" height="24" rx="2" fill="none" strokeWidth="3" />
      <path d="M22 20 L29 27 L42 14" fill="none" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="24" y="32" width="16" height="10" rx="1" />
    </>
  ),
  fdm_printer: (
    <>
      <rect x="8" y="6" width="48" height="6" rx="1" />
      <rect x="8" y="42" width="48" height="6" rx="1" />
      <line x1="10" y1="6" x2="10" y2="48" strokeWidth="3" />
      <line x1="54" y1="6" x2="54" y2="48" strokeWidth="3" />
      <rect x="24" y="18" width="16" height="4" rx="1" />
      <line x1="32" y1="12" x2="32" y2="22" strokeWidth="2" />
    </>
  ),
  resin_printer: (
    <>
      <polygon points="18,10 46,10 40,40 24,40" fill="none" strokeWidth="3" />
      <rect x="20" y="40" width="24" height="8" rx="1" />
      <line x1="32" y1="10" x2="32" y2="2" strokeWidth="3" />
    </>
  ),
  sls_printer: (
    <>
      <rect x="10" y="12" width="44" height="30" rx="2" fill="none" strokeWidth="3" />
      <line x1="10" y1="24" x2="54" y2="24" strokeWidth="2" />
      <line x1="10" y1="32" x2="54" y2="32" strokeWidth="2" />
    </>
  ),
  postprocessing: (
    <>
      <circle cx="32" cy="24" r="16" fill="none" strokeWidth="3" />
      <path d="M32 16 v8 l6 6" fill="none" strokeWidth="3" strokeLinecap="round" />
    </>
  ),
  machine_generic: <rect x="10" y="14" width="44" height="24" rx="3" fill="none" strokeWidth="3" />,
  printer_generic: <rect x="10" y="14" width="44" height="24" rx="3" fill="none" strokeWidth="3" />,
}

export default function MachineIcon({ code, size = 56 }) {
  const shape = ICONS[code] ?? ICONS.machine_generic
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 48"
      fill="currentColor"
      stroke="currentColor"
      className="machine-icon"
    >
      {shape}
    </svg>
  )
}
