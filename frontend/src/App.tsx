import { motion } from "framer-motion";
import { useHass } from "./main";

export function App() {
  const hass = useHass();
  const name = hass?.user?.name ?? "there";

  return (
    <div className="min-h-full w-full flex items-center justify-center bg-bg p-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="
          w-full max-w-md
          rounded-xl
          border border-border
          bg-surface-elevated/80
          backdrop-blur-xl
          shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)]
          px-8 py-10
          flex flex-col items-center text-center gap-3
        "
      >
        <span
          className="inline-flex items-center gap-2 rounded-md px-3 py-1 text-xs font-medium tracking-wide uppercase"
          style={{ background: "var(--color-accent-soft)", color: "var(--color-accent)" }}
        >
          <span className="size-1.5 rounded-full" style={{ background: "var(--color-accent)" }} />
          Pulse
        </span>

        <h1 className="text-3xl font-semibold tracking-tight text-text-primary">
          Hello, {name}
        </h1>

        <p className="text-base text-text-secondary">Pulse is ready.</p>
      </motion.div>
    </div>
  );
}
